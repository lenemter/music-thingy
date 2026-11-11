import { resizeImage } from "./audioTags.ts";
import { coverUrl, templateKey } from "./coverTemplates.ts";
import { loadUser } from "./api.ts";
import type { UserFile } from "./types.ts";

type StoredFile = {
    id?: number
    owner: string
    name: string
    type: string
    duration: number
    size: number
    artist: string
    cover?: string
    blob: Blob
    createdAt: number
}

export type TrackInfo = {
    title?: string
    artist?: string
    cover?: Blob | null | number
}

const DB_NAME = "signal-library";
const STORE_NAME = "files";
const MAX_SIZE = 50 * 1024 * 1024;
const FORMATS = ["MP3", "WAV", "FLAC", "OGG", "M4A", "AAC"];

const audioUrls = new Map<number, string>();

function openDatabase(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, 1);
        request.onupgradeneeded = () => {
            const store = request.result.createObjectStore(STORE_NAME, { keyPath: "id", autoIncrement: true });
            store.createIndex("owner", "owner");
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(new Error("Браузер не дал сохранить музыку"));
    });
}

async function runRequest<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest): Promise<T> {
    const db = await openDatabase();
    return new Promise((resolve, reject) => {
        const request = action(db.transaction(STORE_NAME, mode).objectStore(STORE_NAME));
        request.onsuccess = () => resolve(request.result as T);
        request.onerror = () => reject(new Error("Не удалось сохранить в браузере — возможно, не хватает места"));
    });
}

function getOwner() {
    return loadUser()?.email ?? "guest";
}

function getAudioUrl(record: StoredFile) {
    const id = record.id ?? 0;
    let url = audioUrls.get(id);
    if (!url) {
        url = URL.createObjectURL(record.blob);
        audioUrls.set(id, url);
    }
    return url;
}

function fileFromRecord(record: StoredFile): UserFile {
    return {
        id: record.id ?? 0,
        name: record.name,
        type: record.type,
        duration: record.duration,
        size: record.size,
        audioUrl: getAudioUrl(record),
        isEdited: false,
        artist: record.artist,
        cover: coverUrl(record.cover),
    };
}

function readDuration(file: Blob): Promise<number> {
    return new Promise((resolve) => {
        const url = URL.createObjectURL(file);
        const audio = new Audio();
        let isDone = false;
        function finish(value: number) {
            if (isDone) {
                return;
            }
            isDone = true;
            URL.revokeObjectURL(url);
            resolve(Number.isFinite(value) ? Math.round(value) : 0);
        }
        audio.preload = "metadata";
        audio.onloadedmetadata = () => finish(audio.duration);
        audio.onerror = () => finish(0);
        setTimeout(() => finish(0), 10000);
        audio.src = url;
    });
}

function getFormat(fileName: string) {
    const dot = fileName.lastIndexOf(".");
    return dot === -1 ? "" : fileName.slice(dot + 1).toUpperCase();
}

function getTitle(fileName: string) {
    const dot = fileName.lastIndexOf(".");
    return dot === -1 ? fileName : fileName.slice(0, dot);
}

export async function fetchUploads(): Promise<UserFile[]> {
    const owner = getOwner();
    const records = await runRequest<StoredFile[]>("readonly", (store) => store.index("owner").getAll(owner));
    records.sort((a, b) => b.createdAt - a.createdAt);
    return records.map(fileFromRecord);
}

export async function uploadAudioFile(file: File, title?: string, artist?: string, cover?: string): Promise<UserFile> {
    const type = getFormat(file.name);
    if (!FORMATS.includes(type)) {
        throw new Error("Такой формат не поддерживается — нужен MP3, WAV, FLAC, OGG, M4A или AAC");
    }
    if (file.size > MAX_SIZE) {
        throw new Error("Файл больше 50 МБ");
    }

    const record: StoredFile = {
        owner: getOwner(),
        name: title || getTitle(file.name),
        type: type,
        duration: await readDuration(file),
        size: Math.round(file.size / 1024 / 1024 * 10) / 10,
        artist: artist || "Моя музыка",
        cover: cover,
        blob: file,
        createdAt: Date.now(),
    };
    record.id = await runRequest<number>("readwrite", (store) => store.add(record));
    return fileFromRecord(record);
}

// Ссылка на аудио своего файла по id — нужна, когда трек восстановлен из истории или очереди после перезагрузки
export async function getUploadAudioUrl(id: number): Promise<string | undefined> {
    const record = await runRequest<StoredFile | undefined>("readonly", (store) => store.get(id));
    if (!record || record.owner !== getOwner()) {
        return undefined;
    }
    return getAudioUrl(record);
}

export async function deleteUpload(id: number) {
    await runRequest("readwrite", (store) => store.delete(id));
    const url = audioUrls.get(id);
    if (url) {
        URL.revokeObjectURL(url);
        audioUrls.delete(id);
    }
}

export async function saveTrackInfo(file: UserFile, info: TrackInfo): Promise<UserFile> {
    const record = await runRequest<StoredFile | undefined>("readonly", (store) => store.get(file.id));
    if (!record) {
        throw new Error("Трек не найден — возможно, его уже удалили");
    }

    if (info.title !== undefined) {
        record.name = info.title;
    }
    if (info.artist !== undefined) {
        record.artist = info.artist;
    }
    if (typeof info.cover === "number") {
        record.cover = templateKey(info.cover);
    } else if (info.cover instanceof Blob) {
        record.cover = await resizeImage(info.cover);
    } else if (info.cover === null) {
        record.cover = undefined;
    }

    await runRequest("readwrite", (store) => store.put(record));
    return fileFromRecord(record);
}
