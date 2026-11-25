import { resizeImage } from "./audioTags.ts";
import { coverUrl, templateKey } from "./coverTemplates.ts";
import {
    createUpload,
    fetchUpload,
    fetchUploadList,
    loadUser,
    removeUpload,
    removeUploadCover,
    setUploadCoverImage,
    setUploadCoverTemplate,
    updateUpload,
} from "./api.ts";
import type { UserFileRead } from "./api.ts";
import type { UserFile } from "./types.ts";

export type TrackInfo = {
    title?: string
    artist?: string
    cover?: Blob | null | number
}

const MAX_SIZE = 50 * 1024 * 1024;
const FORMATS = ["MP3", "WAV", "FLAC", "OGG", "M4A", "AAC"];

function fileFromRead(item: UserFileRead): UserFile {
    return {
        id: item.id,
        name: item.name,
        type: item.type,
        duration: item.duration,
        size: item.size,
        audioUrl: item.audio_url,
        isEdited: item.is_edited,
        artist: item.artist,
        cover: coverUrl(item.cover ?? item.cover_url),
    };
}

function getFormat(fileName: string) {
    const dot = fileName.lastIndexOf(".");
    return dot === -1 ? "" : fileName.slice(dot + 1).toUpperCase();
}

export async function fetchUploads(): Promise<UserFile[]> {
    await migrateBrowserUploads();
    const list = await fetchUploadList();
    return list.map(fileFromRead);
}

export async function uploadAudioFile(file: File): Promise<UserFile> {
    if (!FORMATS.includes(getFormat(file.name))) {
        throw new Error("Такой формат не поддерживается — нужен MP3, WAV, FLAC, OGG, M4A или AAC");
    }
    if (file.size > MAX_SIZE) {
        throw new Error("Файл больше 50 МБ");
    }
    return fileFromRead(await createUpload(file, file.name));
}

export async function getUploadAudioUrl(id: number): Promise<string | undefined> {
    try {
        return (await fetchUpload(id)).audio_url;
    } catch {
        return undefined;
    }
}

export async function deleteUpload(id: number) {
    await removeUpload(id);
}

export async function saveTrackInfo(file: UserFile, info: TrackInfo): Promise<UserFile> {
    let result: UserFileRead | null = null;

    const titleChanged = info.title !== undefined && info.title !== file.name;
    const artistChanged = info.artist !== undefined && info.artist !== file.artist;
    if (titleChanged || artistChanged) {
        result = await updateUpload(file.id, { title: info.title, artist: info.artist });
    }

    if (typeof info.cover === "number") {
        result = await setUploadCoverTemplate(file.id, templateKey(info.cover));
    } else if (info.cover instanceof Blob) {
        const resized = await resizeImage(info.cover, 600);
        result = await setUploadCoverImage(file.id, await (await fetch(resized)).blob());
    } else if (info.cover === null) {
        result = await removeUploadCover(file.id);
    }

    return result ? fileFromRead(result) : file;
}


type StoredFile = {
    id: number
    owner: string
    name: string
    artist: string
    cover?: string
    blob: Blob
    type: string
}

const DB_NAME = "signal-library";
const STORE_NAME = "files";
let migration: Promise<void> | null = null;

function openOldDatabase(): Promise<IDBDatabase | null> {
    return new Promise((resolve) => {
        let isNew = false;
        const request = indexedDB.open(DB_NAME, 1);
        request.onupgradeneeded = () => {
            isNew = true;
            const store = request.result.createObjectStore(STORE_NAME, { keyPath: "id", autoIncrement: true });
            store.createIndex("owner", "owner");
        };
        request.onsuccess = () => {
            if (isNew) {
                request.result.close();
                indexedDB.deleteDatabase(DB_NAME);
                resolve(null);
            } else {
                resolve(request.result);
            }
        };
        request.onerror = () => resolve(null);
    });
}

function runOld<T>(db: IDBDatabase, mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest): Promise<T> {
    return new Promise((resolve, reject) => {
        const request = action(db.transaction(STORE_NAME, mode).objectStore(STORE_NAME));
        request.onsuccess = () => resolve(request.result as T);
        request.onerror = () => reject(request.error);
    });
}

function remapLocalIds(owner: string, idMap: Map<number, number>) {
    const keys = ["signal-playlists", "signal-history", "signal-player-session", "signal-liked"].map((name) => name + ":" + owner);

    function walk(value: unknown): unknown {
        if (Array.isArray(value)) {
            return value.map(walk);
        }
        if (typeof value === "string") {
            const match = /^local:(\d+)$/.exec(value);
            const newId = match ? idMap.get(Number(match[1])) : undefined;
            return newId !== undefined ? "local:" + newId : value;
        }
        if (value && typeof value === "object") {
            const result: Record<string, unknown> = {};
            for (const [key, item] of Object.entries(value)) {
                result[key] = walk(item);
            }
            if (result.service === "local" && typeof result.serviceId === "string") {
                const newId = idMap.get(Number(result.serviceId));
                if (newId !== undefined) {
                    result.serviceId = String(newId);
                    delete result.audioUrl;
                }
            }
            return result;
        }
        return value;
    }

    for (const key of keys) {
        try {
            const text = localStorage.getItem(key);
            if (text !== null) {
                localStorage.setItem(key, JSON.stringify(walk(JSON.parse(text))));
            }
        } catch {
            continue;
        }
    }
}

async function runMigration() {
    const owner = loadUser()?.email;
    if (!owner || typeof indexedDB === "undefined") {
        return;
    }
    const db = await openOldDatabase();
    if (!db) {
        return;
    }

    try {
        const records = await runOld<StoredFile[]>(db, "readonly", (store) => store.index("owner").getAll(owner));
        const idMap = new Map<number, number>();

        for (const record of records) {
            try {
                let cover: Blob | string | undefined;
                if (record.cover?.startsWith("template:")) {
                    cover = record.cover;
                } else if (record.cover?.startsWith("data:")) {
                    cover = await (await fetch(record.cover)).blob();
                }
                const fileName = record.name + "." + record.type.toLowerCase();
                const created = await createUpload(record.blob, fileName, { title: record.name, artist: record.artist, cover });
                idMap.set(record.id, created.id);
                await runOld(db, "readwrite", (store) => store.delete(record.id));
            } catch {
                continue;
            }
        }

        if (idMap.size > 0) {
            remapLocalIds(owner, idMap);
        }
    } finally {
        db.close();
    }
}

export function migrateBrowserUploads() {
    if (!migration) {
        migration = runMigration().catch(() => undefined).finally(() => {
            migration = null;
        });
    }
    return migration;
}
