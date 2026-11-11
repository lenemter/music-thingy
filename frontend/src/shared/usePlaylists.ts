import { useEffect, useMemo, useState } from "react";
import { fetchFavorites, fetchMyPlaylists } from "./api.ts";
import { getLikedTracks, getTrackKey, isLikeHidden, subscribeLikes } from "./favorites.ts";
import { getUserPlaylists, subscribePlaylists } from "./playlists.ts";
import { getHistory, getPlaylistPlays, subscribeHistory } from "./history.ts";
import { seededShuffle } from "./waveStream.ts";
import { trackFromFile, trackFromRead } from "./music/convert.ts";
import { getServiceName } from "./music/services.ts";
import { coverUrl } from "./coverTemplates.ts";
import { plural, trackCount } from "./format.ts";
import type { PlaylistRead, ServiceId, TrackRead } from "./music/types.ts";
import type { Service, Track, User, UserFile } from "./types.ts";

export const LIKED_PLAYLIST_ID = "liked";

export type LibraryPlaylist = {
    id: string
    kind: "liked" | "user" | "service"
    name: string
    subtitle: string
    tracks: Track[] | null
    tracksCount: number
    duration: number
    cover?: string
    covers: string[]
    service?: ServiceId
    serviceId?: string
    externalUrl?: string
    unavailable?: string
}

const PLAYLISTS_CACHE = "signal-service-playlists";
const FAVORITES_CACHE = "signal-service-favorites";

function readCache<T>(name: string, email: string | undefined): T[] {
    if (!email) {
        return [];
    }
    try {
        const value = JSON.parse(localStorage.getItem(name + ":" + email) ?? "[]");
        return Array.isArray(value) ? value : [];
    } catch {
        return [];
    }
}

function writeCache(name: string, email: string, value: unknown[]) {
    try {
        localStorage.setItem(name + ":" + email, JSON.stringify(value));
    } catch {
        return;
    }
}

// Свежие данные — для включённых сервисов, из кэша — для отключённых, чтобы их плейлисты были видны как «недоступные».
function mergeWithCache<T extends { service: ServiceId }>(fresh: T[], cached: T[], online: string[]) {
    return [...fresh, ...cached.filter((item) => !online.includes(item.service))];
}

// offline — сервисы, которые точно отключены (пока статусы не загружены, список пустой)
function resolveTracks(tracks: Track[], files: UserFile[], offline: string[]) {
    const likedKeys = new Set(getLikedTracks().map(getTrackKey));
    const result: Track[] = [];
    for (const track of tracks) {
        if (track.service === "local") {
            const file = files.find((item) => String(item.id) === track.serviceId);
            if (file) {
                result.push(trackFromFile(file));
            }
        } else {
            const isOffline = track.service !== undefined && offline.includes(track.service);
            result.push({
                ...track,
                liked: likedKeys.has(getTrackKey(track)),
                unavailable: isOffline && track.service ? getServiceName(track.service) : undefined,
            });
        }
    }
    return result;
}

function getCovers(tracks: Track[]) {
    const covers: string[] = [];
    for (const track of tracks) {
        if (track.cover && !covers.includes(track.cover)) {
            covers.push(track.cover);
        }
        if (covers.length === 4) {
            break;
        }
    }
    return covers;
}

function describeTracks(tracks: Track[]) {
    const sources = new Set(tracks.map((track) => track.service ?? track.source));
    const text = trackCount(tracks.length);
    if (sources.size > 1) {
        return text + " из " + sources.size + " " + plural(sources.size, "сервиса", "сервисов", "сервисов");
    }
    return text;
}

function sumDuration(tracks: Track[]) {
    return tracks.reduce((total, track) => total + (track.duration || 0), 0);
}

export function usePlaylists(user: User | null, services: Service[], files: UserFile[], servicesReady: boolean) {
    const email = user?.email;
    const [version, setVersion] = useState(0);
    const [servicePlaylists, setServicePlaylists] = useState<PlaylistRead[]>(() => readCache(PLAYLISTS_CACHE, email));
    const [serviceFavorites, setServiceFavorites] = useState<TrackRead[]>(() => readCache(FAVORITES_CACHE, email));
    const [isLoading, setIsLoading] = useState(false);
    const online = services.filter((service) => service.online).map((service) => service.id);
    const onlineKey = online.join(",");
    const offline = servicesReady ? services.filter((service) => !service.online).map((service) => service.id as string) : [];
    const offlineKey = offline.join(",");

    useEffect(() => {
        const update = () => setVersion((value) => value + 1);
        const stopLikes = subscribeLikes(update);
        const stopPlaylists = subscribePlaylists(update);
        const stopHistory = subscribeHistory(update);
        return () => {
            stopLikes();
            stopPlaylists();
            stopHistory();
        };
    }, []);

    useEffect(() => {
        setServicePlaylists(readCache(PLAYLISTS_CACHE, email));
        setServiceFavorites(readCache(FAVORITES_CACHE, email));
        setVersion((value) => value + 1);
    }, [email]);

    useEffect(() => {
        if (!email || onlineKey === "") {
            setIsLoading(false);
            return;
        }

        let isCancelled = false;
        const onlineIds = onlineKey.split(",");
        setIsLoading(true);

        Promise.allSettled([fetchMyPlaylists(), fetchFavorites()]).then(([playlistsResult, favoritesResult]) => {
            if (isCancelled) {
                return;
            }
            if (playlistsResult.status === "fulfilled") {
                const merged = mergeWithCache(playlistsResult.value, readCache<PlaylistRead>(PLAYLISTS_CACHE, email), onlineIds)
                    .map((item) => ({ ...item, tracks: null }));
                writeCache(PLAYLISTS_CACHE, email, merged);
                setServicePlaylists(merged);
            }
            if (favoritesResult.status === "fulfilled") {
                const merged = mergeWithCache(favoritesResult.value, readCache<TrackRead>(FAVORITES_CACHE, email), onlineIds);
                writeCache(FAVORITES_CACHE, email, merged);
                setServiceFavorites(merged);
            }
            setIsLoading(false);
        });

        return () => {
            isCancelled = true;
        };
    }, [email, onlineKey]);

    const playlists = useMemo(() => {
        const result: LibraryPlaylist[] = [];

        const liked = resolveTracks(getLikedTracks(), files, offline).map((track) => ({ ...track, liked: true }));
        const likedKeys = new Set(liked.map(getTrackKey));
        for (const item of serviceFavorites) {
            const track = trackFromRead(item);
            if (offline.includes(item.service)) {
                track.unavailable = getServiceName(item.service);
            }
            if (!likedKeys.has(getTrackKey(track)) && !isLikeHidden(item.service, item.service_id)) {
                likedKeys.add(getTrackKey(track));
                liked.push({ ...track, liked: true });
            }
        }
        result.push({
            id: LIKED_PLAYLIST_ID,
            kind: "liked",
            name: "Понравившиеся",
            subtitle: liked.length > 0 ? "Собирается сам · " + describeTracks(liked) : "Собирается сам из ваших лайков",
            tracks: liked,
            tracksCount: liked.length,
            duration: sumDuration(liked),
            covers: getCovers(liked),
        });

        for (const playlist of getUserPlaylists()) {
            const tracks = resolveTracks(playlist.tracks, files, offline);
            result.push({
                id: "user:" + playlist.id,
                kind: "user",
                name: playlist.name,
                subtitle: tracks.length > 0 ? "Ваш плейлист · " + describeTracks(tracks) : "Ваш плейлист · пока пусто",
                tracks: tracks,
                tracksCount: tracks.length,
                duration: sumDuration(tracks),
                covers: getCovers(tracks),
            });
        }

        for (const playlist of servicePlaylists) {
            const serviceName = getServiceName(playlist.service);
            const isOnline = !offline.includes(playlist.service);
            const count = playlist.tracks_count ?? 0;
            result.push({
                id: "service:" + playlist.service + ":" + playlist.service_id,
                kind: "service",
                name: playlist.name,
                subtitle: isOnline
                    ? serviceName + (count > 0 ? " · " + trackCount(count) : "")
                    : "Недоступно · подключите сервис " + serviceName,
                tracks: null,
                tracksCount: count,
                duration: 0,
                cover: coverUrl(playlist.cover) ?? playlist.artwork_url ?? undefined,
                covers: [],
                service: playlist.service,
                serviceId: playlist.service_id,
                externalUrl: playlist.external_url ?? undefined,
                unavailable: isOnline ? undefined : serviceName,
            });
        }

        return result;
        // version меняется, когда меняются лайки или свои плейлисты в localStorage
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [version, files, servicePlaylists, serviceFavorites, onlineKey, offlineKey]);

    const recentTracks = useMemo(
        () => resolveTracks(getHistory(), files, offline).slice(0, RECENT_COUNT),
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [version, files, offlineKey],
    );

    // «Продолжить слушать»: сначала плейлисты, которые недавно включали, потом остальные
    const continuePlaylists = useMemo(() => {
        const plays = getPlaylistPlays();
        return [...playlists]
            .filter((playlist) => playlist.kind !== "liked" || playlist.tracksCount > 0 || plays[playlist.id])
            .sort((a, b) => (plays[b.id] ?? 0) - (plays[a.id] ?? 0))
            .slice(0, CONTINUE_COUNT);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [playlists, version]);

    const wave = useMemo(() => buildWave(playlists, recentTracks, getHistory()), [playlists, recentTracks]);

    return { playlists, isLoading, recentTracks, continuePlaylists, wave };
}

const RECENT_COUNT = 10;
const CONTINUE_COUNT = 5;

export type DailyWave = {
    seed: string
    date: string
    title: string
    description: string
    tracks: Track[]
    duration: number
}

function getWaveTitle(hour: number) {
    if (hour >= 5 && hour < 12) {
        return "Утренний эфир";
    }
    if (hour >= 12 && hour < 17) {
        return "Дневной эфир";
    }
    if (hour >= 17 && hour < 22) {
        return "Эфир на закате";
    }
    return "Ночной эфир";
}

function joinNames(names: string[]) {
    if (names.length <= 1) {
        return names[0] ?? "";
    }
    return names.slice(0, -1).join(", ") + " и " + names[names.length - 1];
}

function buildWave(playlists: LibraryPlaylist[], recent: Track[], history: Track[]): DailyWave {
    const now = new Date();
    const day = String(now.getDate()).padStart(2, "0") + "." + String(now.getMonth() + 1).padStart(2, "0");
    const pool = new Map<string, Track>();
    const add = (track: Track) => {
        // демо-треки без сервиса не играют — в волну их не берём
        if (track.service && !track.unavailable && !pool.has(getTrackKey(track))) {
            pool.set(getTrackKey(track), track);
        }
    };

    playlists.forEach((playlist) => playlist.tracks?.forEach(add));
    recent.forEach(add);
    const historyKeys = new Set(history.map(getTrackKey));
    const seed = day + "." + now.getFullYear();
    const tracks = seededShuffle([...pool.values()], seed);
    const duration = sumDuration(tracks);
    const names = [...new Set(tracks.map((track) => getServiceName(track.service ?? track.source)))];
    const fromHistory = tracks.filter((track) => historyKeys.has(getTrackKey(track))).length;

    let description = "Поставьте лайки, соберите плейлист или загрузите свою музыку — волна дня соберётся из них.";
    if (tracks.length > 0) {
        description = trackCount(tracks.length) + " из ваших лайков, плейлистов" + (fromHistory > 0 ? " и недавних прослушиваний" : "")
            + (names.length > 0 ? ". Источники: " + joinNames(names) : "")
            + ". Один поток — без переключения приложений.";
    }

    return { seed, date: day, title: getWaveTitle(now.getHours()), description, tracks, duration };
}
