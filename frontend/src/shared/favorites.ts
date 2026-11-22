import type { Track } from "./types.ts";
import { likeTrack, loadUser, unlikeTrack } from "./api.ts";

// Лайки хранятся на сервере (PUT/DELETE /api/music/tracks/{service}/{id}/like, список — /api/music/me/liked).
// Здесь — кэш этого списка в браузере, чтобы сердечко менялось сразу, а «Понравившиеся» открывались без ожидания.

type LikedEntry = {
    key: string
    track: Track
    likedAt: number
}

const CACHE_KEY = "signal-likes-cache";
// Лайки, поставленные до появления бэкенда, — переносятся на сервер один раз
const LEGACY_KEY = "signal-liked";
// Лайки из самих сервисов, которые пользователь снял у нас, но сервис не дал снять у себя
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
        return;
    }
}

function notify() {
    listeners.forEach((listener) => listener());
}

export function getTrackKey(track: Track) {
    return track.service && track.serviceId ? track.service + ":" + track.serviceId : track.id;
}

function getLikeKey(service: string, serviceId: string) {
    return service + ":" + serviceId;
}

function snapshot(track: Track): Track {
    const copy: Track = { ...track, liked: true };
    delete copy.unavailable;
    if (track.service === "local") {
        delete copy.audioUrl;
    }
    return copy;
}

export function subscribeLikes(listener: () => void) {
    listeners.add(listener);
    return () => {
        listeners.delete(listener);
    };
}

export function getLikedTracks(): Track[] {
    const hidden = readList<string>(HIDDEN_KEY);
    return readList<LikedEntry>(CACHE_KEY)
        .filter((entry) => !hidden.includes(entry.key))
        .sort((a, b) => b.likedAt - a.likedAt)
        .map((entry) => ({ ...entry.track, liked: true }));
}

export function isTrackLiked(service: string, serviceId: string) {
    const key = getLikeKey(service, serviceId);
    return readList<LikedEntry>(CACHE_KEY).some((entry) => entry.key === key) && !isLikeHidden(service, serviceId);
}

export function isLikeHidden(service: string, serviceId: string) {
    return readList<string>(HIDDEN_KEY).includes(getLikeKey(service, serviceId));
}

// Свежий список с сервера (порядок — как пришёл, новые первыми). Демо-треки без сервиса остаются локальными.
export function setLikedCache(tracks: Track[]) {
    const now = Date.now();
    const localOnly = readList<LikedEntry>(CACHE_KEY).filter((entry) => !entry.track.service);
    const fromServer = tracks.map((track, index) => ({ key: getTrackKey(track), track: snapshot(track), likedAt: now - index }));
    writeList(CACHE_KEY, [...localOnly, ...fromServer]);
    notify();
}

export function takeLegacyLikes(): Track[] {
    const entries = readList<LikedEntry>(LEGACY_KEY);
    if (entries.length > 0) {
        try {
            localStorage.removeItem(LEGACY_KEY + ":" + getOwner());
        } catch {
            return [];
        }
    }
    return entries.sort((a, b) => a.likedAt - b.likedAt).map((entry) => entry.track);
}

function likeInfo(track: Track) {
    // Обложку-картинку из браузера (data:) на сервер не отправляем — он подтянет свою
    const cover = track.cover && !track.cover.startsWith("data:") && !track.cover.startsWith("blob:") ? track.cover : undefined;
    return { title: track.title, artist: track.artist, cover, duration: track.duration };
}

export async function sendLike(track: Track) {
    if (track.service && track.serviceId) {
        await likeTrack(track.service, track.serviceId, likeInfo(track));
    }
}

export async function setTrackLiked(track: Track, liked: boolean) {
    const key = getTrackKey(track);
    const before = readList<LikedEntry>(CACHE_KEY);
    const hiddenBefore = readList<string>(HIDDEN_KEY);

    // Сразу меняем кэш, чтобы интерфейс не ждал сервер
    const entries = before.filter((entry) => entry.key !== key);
    if (liked) {
        entries.push({ key, track: snapshot(track), likedAt: Date.now() });
    }
    writeList(CACHE_KEY, entries);
    writeList(HIDDEN_KEY, hiddenBefore.filter((item) => item !== key));
    notify();

    if (!track.service || !track.serviceId) {
        return;
    }

    try {
        if (liked) {
            await sendLike(track);
        } else {
            const result = await unlikeTrack(track.service, track.serviceId);
            if (!result.synced) {
                // Сервис не дал снять лайк у себя — прячем трек, чтобы он не вернулся при следующей загрузке списка
                writeList(HIDDEN_KEY, [...readList<string>(HIDDEN_KEY).filter((item) => item !== key), key]);
                notify();
            }
        }
    } catch (err) {
        writeList(CACHE_KEY, before);
        writeList(HIDDEN_KEY, hiddenBefore);
        notify();
        throw err;
    }
}
