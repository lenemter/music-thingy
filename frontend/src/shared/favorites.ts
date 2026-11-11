import type { Track } from "./types.ts";
import { loadUser } from "./api.ts";

type LikedEntry = {
    key: string
    track: Track
    likedAt: number
}

const LIKED_KEY = "signal-liked";
const HIDDEN_KEY = "signal-unliked";

const listeners = new Set<() => void>();

function getOwner() {
    return loadUser()?.email ?? "guest";
}

function readList<T>(name: string): T[] {
    try {
        const value = JSON.parse(localStorage.getItem(name + ":" + getOwner()) ?? "[]");
        return Array.isArray(value) ? value : [];
    } catch {
        return [];
    }
}

function writeList(name: string, value: unknown[]) {
    try {
        localStorage.setItem(name + ":" + getOwner(), JSON.stringify(value));
    } catch {
        throw new Error("Не удалось сохранить в браузере");
    }
}

export function getTrackKey(track: Track) {
    return track.service && track.serviceId ? track.service + ":" + track.serviceId : track.id;
}

function getLikeKey(service: string, serviceId: string) {
    return service + ":" + serviceId;
}

export function subscribeLikes(listener: () => void) {
    listeners.add(listener);
    return () => {
        listeners.delete(listener);
    };
}

export function getLikedTracks(): Track[] {
    return readList<LikedEntry>(LIKED_KEY)
        .sort((a, b) => b.likedAt - a.likedAt)
        .map((entry) => ({ ...entry.track, liked: true }));
}

export function isTrackLiked(service: string, serviceId: string) {
    const key = getLikeKey(service, serviceId);
    return readList<LikedEntry>(LIKED_KEY).some((entry) => entry.key === key);
}

// Лайки, поставленные в самих сервисах: если пользователь снял лайк у нас, прячем трек из «Понравившихся».
export function isLikeHidden(service: string, serviceId: string) {
    return readList<string>(HIDDEN_KEY).includes(getLikeKey(service, serviceId));
}

export async function setTrackLiked(track: Track, liked: boolean) {
    const key = getTrackKey(track);
    const entries = readList<LikedEntry>(LIKED_KEY).filter((entry) => entry.key !== key);
    const hidden = readList<string>(HIDDEN_KEY).filter((item) => item !== key);

    if (liked) {
        const snapshot: Track = { ...track, liked: true };
        delete snapshot.unavailable;
        if (track.service === "local") {
            delete snapshot.audioUrl;
        }
        entries.push({ key, track: snapshot, likedAt: Date.now() });
    } else {
        hidden.push(key);
    }

    writeList(LIKED_KEY, entries);
    writeList(HIDDEN_KEY, hidden);
    listeners.forEach((listener) => listener());
}
