import { ApiError, removeCover, updateUpload, uploadCover } from "./api.ts";
import { resizeImage } from "./audioTags.ts";
import { coverUrl, templateImage, templateKey } from "./coverTemplates.ts";
import type { UserFile } from "./types.ts";

type TrackOverride = {
    title?: string
    artist?: string
    cover?: string | null
}

export type TrackInfo = {
    title?: string
    artist?: string
    cover?: Blob | null | number
}

const STORAGE_KEY = "signal-library";

function loadOverrides(): Record<string, TrackOverride> {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}");
    } catch {
        return {};
    }
}

function saveOverrides(all: Record<string, TrackOverride>) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
    } catch {
        throw new Error("В браузере не хватает места, попробуйте картинку поменьше");
    }
}

export function getOverride(id: number | string): TrackOverride | undefined {
    return loadOverrides()[String(id)];
}

export function applyOverride(file: UserFile): UserFile {
    const override = getOverride(file.id);
    if (!override) {
        return file;
    }
    return {
        ...file,
        name: override.title ?? file.name,
        artist: override.artist ?? file.artist,
        cover: override.cover === null ? undefined : coverUrl(override.cover ?? file.cover),
    };
}

export function removeOverride(id: number) {
    const all = loadOverrides();
    delete all[String(id)];
    saveOverrides(all);
}

function isUnsupported(error: unknown) {
    return error instanceof ApiError && (error.status === 404 || error.status === 405);
}

export async function saveTrackInfo(file: UserFile, info: TrackInfo) {
    let result = file;
    const override: TrackOverride = { ...getOverride(file.id) };
    let savedLocally = false;

    if (info.title !== undefined || info.artist !== undefined) {
        const title = info.title ?? file.name;
        const artist = info.artist ?? file.artist;
        try {
            result = await updateUpload(file.id, { title, artist });
            delete override.title;
            delete override.artist;
        } catch (error) {
            if (!isUnsupported(error)) {
                throw error;
            }
            override.title = title;
            override.artist = artist;
            savedLocally = true;
        }
    }

    if (typeof info.cover === "number") {
        try {
            result = await uploadCover(file.id, await templateImage(info.cover));
            delete override.cover;
        } catch (error) {
            if (!isUnsupported(error)) {
                throw error;
            }
            override.cover = templateKey(info.cover);
            savedLocally = true;
        }
    } else if (info.cover instanceof Blob) {
        try {
            result = await uploadCover(file.id, info.cover);
            delete override.cover;
        } catch (error) {
            if (!isUnsupported(error)) {
                throw error;
            }
            override.cover = await resizeImage(info.cover);
            savedLocally = true;
        }
    } else if (info.cover === null) {
        try {
            await removeCover(file.id);
            result = { ...result, cover: undefined };
            delete override.cover;
        } catch (error) {
            if (!isUnsupported(error)) {
                throw error;
            }
            override.cover = null;
            savedLocally = true;
        }
    }

    const all = loadOverrides();
    if (Object.keys(override).length > 0) {
        all[String(file.id)] = override;
    } else {
        delete all[String(file.id)];
    }
    saveOverrides(all);

    return { file: applyOverride(result), savedLocally };
}
