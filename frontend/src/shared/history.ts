import type { Track } from "./types.ts";
import { loadUser } from "./api.ts";
import { getTrackKey } from "./favorites.ts";

// История прослушиваний и запусков плейлистов — пока в браузере, отдельно для каждого пользователя.
type HistoryEntry = {
    key: string
    track: Track
    playedAt: number
}

const HISTORY_KEY = "signal-history";
const PLAYLIST_PLAYS_KEY = "signal-playlist-plays";
const MAX_HISTORY = 100;

const listeners = new Set<() => void>();

function storageKey(name: string) {
    return name + ":" + (loadUser()?.email ?? "guest");
}

function read<T>(name: string, fallback: T): T {
    try {
        const text = localStorage.getItem(storageKey(name));
        return text === null ? fallback : JSON.parse(text);
    } catch {
        return fallback;
    }
}

function write(name: string, value: unknown) {
    try {
        localStorage.setItem(storageKey(name), JSON.stringify(value));
    } catch {
        return;
    }
    listeners.forEach((listener) => listener());
}

export function subscribeHistory(listener: () => void) {
    listeners.add(listener);
    return () => {
        listeners.delete(listener);
    };
}

export function getHistory(): Track[] {
    const entries = read<HistoryEntry[]>(HISTORY_KEY, []);
    return Array.isArray(entries) ? entries.map((entry) => entry.track) : [];
}

export function addToHistory(track: Track) {
    // Демо-треки без сервиса в историю не попадают
    if (!track.service || !track.serviceId) {
        return;
    }
    const key = getTrackKey(track);
    const entries = read<HistoryEntry[]>(HISTORY_KEY, []).filter((entry) => entry.key !== key);
    const snapshot: Track = { ...track };
    delete snapshot.liked;
    delete snapshot.unavailable;
    if (track.service === "local") {
        delete snapshot.audioUrl;
    }
    write(HISTORY_KEY, [{ key, track: snapshot, playedAt: Date.now() }, ...entries].slice(0, MAX_HISTORY));
}

export function getPlaylistPlays(): Record<string, number> {
    return read<Record<string, number>>(PLAYLIST_PLAYS_KEY, {});
}

export function markPlaylistPlayed(playlistId: string) {
    write(PLAYLIST_PLAYS_KEY, { ...getPlaylistPlays(), [playlistId]: Date.now() });
}
