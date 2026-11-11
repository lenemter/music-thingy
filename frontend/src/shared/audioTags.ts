export type AudioTags = {
    title?: string
    artist?: string
    cover?: Blob
}

function readText(bytes: Uint8Array, encoding: number) {
    let end = bytes.length;
    while (end > 0 && bytes[end - 1] === 0) {
        end--;
    }
    const data = bytes.subarray(0, end);

    if (encoding === 1 || encoding === 2) {
        return new TextDecoder(encoding === 2 ? "utf-16be" : "utf-16").decode(data).replace(/\0/g, "").trim();
    }
    return new TextDecoder(encoding === 3 ? "utf-8" : "windows-1252").decode(data).replace(/\0/g, "").trim();
}

function findTextEnd(bytes: Uint8Array, start: number, encoding: number) {
    const isWide = encoding === 1 || encoding === 2;
    for (let i = start; i < bytes.length; i += isWide ? 2 : 1) {
        if (bytes[i] === 0 && (!isWide || bytes[i + 1] === 0)) {
            return i;
        }
    }
    return bytes.length;
}

function syncsafe(bytes: Uint8Array, offset: number) {
    return (bytes[offset] << 21) | (bytes[offset + 1] << 14) | (bytes[offset + 2] << 7) | bytes[offset + 3];
}

function readId3(bytes: Uint8Array): AudioTags {
    const tags: AudioTags = {};
    const version = bytes[3];
    const flags = bytes[5];
    const tagEnd = Math.min(10 + syncsafe(bytes, 6), bytes.length);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);

    let offset = 10;
    if (flags & 0x40) {
        offset += version === 4 ? syncsafe(bytes, 10) : view.getUint32(10) + 4;
    }

    while (offset + 10 <= tagEnd) {
        const id = String.fromCharCode(...bytes.subarray(offset, offset + 4));
        if (!/^[A-Z0-9]{4}$/.test(id)) {
            break;
        }
        const size = version === 4 ? syncsafe(bytes, offset + 4) : view.getUint32(offset + 4);
        const body = bytes.subarray(offset + 10, offset + 10 + size);
        offset += 10 + size;

        if (body.length === 0) {
            continue;
        }

        if (id === "TIT2") {
            tags.title = readText(body.subarray(1), body[0]);
        } else if (id === "TPE1") {
            tags.artist = readText(body.subarray(1), body[0]);
        } else if (id === "APIC" && !tags.cover) {
            const encoding = body[0];
            const mimeEnd = findTextEnd(body, 1, 0);
            const mime = readText(body.subarray(1, mimeEnd), 0) || "image/jpeg";
            const descriptionStart = mimeEnd + 2;
            const descriptionEnd = findTextEnd(body, descriptionStart, encoding);
            const dataStart = descriptionEnd + (encoding === 1 || encoding === 2 ? 2 : 1);
            const image = body.slice(dataStart);
            if (image.length > 0) {
                tags.cover = new Blob([image], { type: mime.includes("/") ? mime : "image/" + mime.toLowerCase() });
            }
        }
    }

    return tags;
}

function readFlac(bytes: Uint8Array): AudioTags {
    const tags: AudioTags = {};
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    let offset = 4;
    let isLast = false;

    while (!isLast && offset + 4 <= bytes.length) {
        isLast = (bytes[offset] & 0x80) !== 0;
        const type = bytes[offset] & 0x7f;
        const length = (bytes[offset + 1] << 16) | (bytes[offset + 2] << 8) | bytes[offset + 3];
        const start = offset + 4;
        offset = start + length;
        if (offset > bytes.length) {
            break;
        }

        if (type === 4) {
            let position = start;
            const vendorLength = view.getUint32(position, true);
            position += 4 + vendorLength;
            const count = view.getUint32(position, true);
            position += 4;
            for (let i = 0; i < count && position + 4 <= offset; i++) {
                const commentLength = view.getUint32(position, true);
                const comment = new TextDecoder("utf-8").decode(bytes.subarray(position + 4, position + 4 + commentLength));
                position += 4 + commentLength;
                const separator = comment.indexOf("=");
                const key = comment.slice(0, separator).toUpperCase();
                const value = comment.slice(separator + 1).trim();
                if (key === "TITLE" && !tags.title) {
                    tags.title = value;
                }
                if (key === "ARTIST" && !tags.artist) {
                    tags.artist = value;
                }
            }
        }

        if (type === 6 && !tags.cover) {
            let position = start + 4;
            const mimeLength = view.getUint32(position);
            const mime = new TextDecoder().decode(bytes.subarray(position + 4, position + 4 + mimeLength));
            position += 4 + mimeLength;
            const descriptionLength = view.getUint32(position);
            position += 4 + descriptionLength + 16;
            const dataLength = view.getUint32(position);
            const image = bytes.slice(position + 4, position + 4 + dataLength);
            if (image.length > 0) {
                tags.cover = new Blob([image], { type: mime || "image/jpeg" });
            }
        }
    }

    return tags;
}

export async function readAudioTags(data: Blob): Promise<AudioTags> {
    const head = new Uint8Array(await data.slice(0, 10).arrayBuffer());

    if (head[0] === 0x49 && head[1] === 0x44 && head[2] === 0x33) {
        const size = 10 + syncsafe(head, 6);
        const bytes = new Uint8Array(await data.slice(0, size).arrayBuffer());
        return readId3(bytes);
    }

    if (head[0] === 0x66 && head[1] === 0x4c && head[2] === 0x61 && head[3] === 0x43) {
        const bytes = new Uint8Array(await data.slice(0, 8 * 1024 * 1024).arrayBuffer());
        return readFlac(bytes);
    }

    return {};
}

export async function readTagsFromUrl(url: string): Promise<AudioTags> {
    const response = await fetch(url, { headers: { Range: "bytes=0-8388607" } });
    if (!response.ok) {
        throw new Error("Не удалось прочитать файл");
    }
    return readAudioTags(await response.blob());
}

export function resizeImage(image: Blob, size = 320): Promise<string> {
    return new Promise((resolve, reject) => {
        const url = URL.createObjectURL(image);
        const img = new Image();
        img.onload = () => {
            const scale = Math.min(1, size / Math.max(img.width, img.height));
            const canvas = document.createElement("canvas");
            canvas.width = Math.round(img.width * scale);
            canvas.height = Math.round(img.height * scale);
            canvas.getContext("2d")?.drawImage(img, 0, 0, canvas.width, canvas.height);
            URL.revokeObjectURL(url);
            resolve(canvas.toDataURL("image/jpeg", 0.85));
        };
        img.onerror = () => {
            URL.revokeObjectURL(url);
            reject(new Error("Не удалось открыть картинку"));
        };
        img.src = url;
    });
}
