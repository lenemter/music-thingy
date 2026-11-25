import type { Track } from "../types.ts";
import { loadUser } from "../api.ts";

export type Trim = {
    start: number
    end: number
}

export const MIN_TRIM_LENGTH = 3;

function storageKey() {
    return "signal-trims:" + (loadUser()?.email ?? "guest");
}

function trackKey(track: Track) {
    return track.service && track.serviceId ? track.service + ":" + track.serviceId : track.id;
}

function readAll(): Record<string, Trim> {
    try {
        const value = JSON.parse(localStorage.getItem(storageKey()) ?? "{}");
        return value && typeof value === "object" ? value : {};
    } catch {
        return {};
    }
}

export function getTrim(track: Track | undefined): Trim | null {
    if (!track) {
        return null;
    }
    const trim = readAll()[trackKey(track)];
    return trim && trim.end > trim.start ? trim : null;
}

export function saveTrim(track: Track, start: number, end: number, duration: number) {
    const all = readAll();
    const key = trackKey(track);
    if (start <= 0.5 && end >= duration - 0.5) {
        delete all[key];
    } else {
        all[key] = { start: Math.max(0, start), end: Math.min(duration, end) };
    }
    try {
        localStorage.setItem(storageKey(), JSON.stringify(all));
    } catch {
        throw new Error("Не удалось сохранить обрезку в браузере");
    }
}

export function playedDuration(track: Track, duration: number) {
    const trim = getTrim(track);
    return trim ? Math.max(0, Math.round(trim.end - trim.start)) : duration;
}
