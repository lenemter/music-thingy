import type { Track } from "../types.ts";
import { loadUser } from "../api.ts";

// Что играло до перезагрузки: окно очереди вокруг текущего трека и, если играла волна, её зерно.
export type PlayerSession = {
    queue: Track[]
    index: number
    waveSeed?: string
}

const KEEP_AROUND = 3;

function storageKey() {
    return "signal-player-session:" + (loadUser()?.email ?? "guest");
}

function clean(track: Track): Track {
    const copy: Track = { ...track };
    delete copy.liked;
    delete copy.unavailable;
    if (track.service === "local") {
        // ссылка на файл живёт только до перезагрузки — при запуске её получим заново
        delete copy.audioUrl;
    }
    return copy;
}

export function loadSession(): PlayerSession | null {
    try {
        const value = JSON.parse(localStorage.getItem(storageKey()) ?? "null");
        if (!value || !Array.isArray(value.queue) || value.queue.length === 0) {
            return null;
        }
        const index = Math.min(Math.max(0, Number(value.index) || 0), value.queue.length - 1);
        return { queue: value.queue, index, waveSeed: typeof value.waveSeed === "string" ? value.waveSeed : undefined };
    } catch {
        return null;
    }
}

export function saveSession(queue: Track[], index: number, waveSeed?: string) {
    if (queue.length === 0 || !queue[index]) {
        return;
    }
    // Сохраняем только ближайшее: 3 сыгранных, текущий и 3 следующих
    const start = Math.max(0, index - KEEP_AROUND);
    const windowed = queue.slice(start, index + KEEP_AROUND + 1).map(clean);
    try {
        localStorage.setItem(storageKey(), JSON.stringify({ queue: windowed, index: index - start, waveSeed }));
    } catch {
        return;
    }
}
