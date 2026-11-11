import type { Track } from "./types.ts";
import { loadUser } from "./api.ts";
import { getTrackKey } from "./favorites.ts";

// Свои плейлисты пока хранятся в браузере (на бэкенде их ещё нет), отдельно для каждого пользователя.
export type UserPlaylist = {
    id: string
    name: string
    tracks: Track[]
    createdAt: number
}

const listeners = new Set<() => void>();
const addListeners = new Set<(track: Track) => void>();

function getStorageKey() {
    return "signal-playlists:" + (loadUser()?.email ?? "guest");
}

function save(playlists: UserPlaylist[]) {
    try {
        localStorage.setItem(getStorageKey(), JSON.stringify(playlists));
    } catch {
        throw new Error("Не удалось сохранить плейлист в браузере");
    }
    listeners.forEach((listener) => listener());
}

function snapshot(track: Track): Track {
    const copy: Track = { ...track };
    delete copy.liked;
    delete copy.unavailable;
    if (track.service === "local") {
        delete copy.audioUrl;
    }
    return copy;
}

export function subscribePlaylists(listener: () => void) {
    listeners.add(listener);
    return () => {
        listeners.delete(listener);
    };
}

export function getUserPlaylists(): UserPlaylist[] {
    try {
        const value = JSON.parse(localStorage.getItem(getStorageKey()) ?? "[]");
        return Array.isArray(value) ? value : [];
    } catch {
        return [];
    }
}

export function createPlaylist(name: string, firstTrack?: Track | Track[]): UserPlaylist {
    const initial = Array.isArray(firstTrack) ? firstTrack : firstTrack ? [firstTrack] : [];
    const playlist: UserPlaylist = {
        id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
        name: name,
        tracks: initial.map(snapshot),
        createdAt: Date.now(),
    };
    save([playlist, ...getUserPlaylists()]);
    return playlist;
}

export function renamePlaylist(id: string, name: string) {
    save(getUserPlaylists().map((item) => (item.id === id ? { ...item, name } : item)));
}

export function deletePlaylist(id: string) {
    save(getUserPlaylists().filter((item) => item.id !== id));
}

export function hasTrack(playlist: UserPlaylist, track: Track) {
    const key = getTrackKey(track);
    return playlist.tracks.some((item) => getTrackKey(item) === key);
}

export function addTrackToPlaylist(id: string, track: Track) {
    save(getUserPlaylists().map((item) => {
        if (item.id !== id || hasTrack(item, track)) {
            return item;
        }
        return { ...item, tracks: [...item.tracks, snapshot(track)] };
    }));
}

export function removeTrackFromPlaylist(id: string, track: Track) {
    const key = getTrackKey(track);
    save(getUserPlaylists().map((item) => {
        if (item.id !== id) {
            return item;
        }
        return { ...item, tracks: item.tracks.filter((entry) => getTrackKey(entry) !== key) };
    }));
}

// Кнопка «+» у трека открывает окно выбора плейлиста, которое живёт в App.
export function openAddToPlaylist(track: Track) {
    addListeners.forEach((listener) => listener(track));
}

export function subscribeAddToPlaylist(listener: (track: Track) => void) {
    addListeners.add(listener);
    return () => {
        addListeners.delete(listener);
    };
}
