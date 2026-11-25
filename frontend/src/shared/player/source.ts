import { fetchTrack } from "../api.ts";
import { getUploadAudioUrl } from "../library.ts";
import type { Track } from "../types.ts";
import { createAudioEngine } from "./audioEngine.ts";
import { createSoundCloudEngine } from "./soundcloudEngine.ts";
import { createYouTubeEngine } from "./youtubeEngine.ts";
import type { EngineEvents, PlaybackSource, PlayerEngine } from "./types.ts";

const PREFETCH_TTL_MS = 10 * 60 * 1000;
const prefetched = new Map<string, { promise: Promise<PlaybackSource>, at: number }>();
let warmAudio: HTMLAudioElement | null = null;

function sourceKey(track: Track) {
    return track.service && track.serviceId ? track.service + ":" + track.serviceId : track.id;
}

export function prefetchSource(track: Track) {
    const key = sourceKey(track);
    const cached = prefetched.get(key);
    if (cached && Date.now() - cached.at < PREFETCH_TTL_MS) {
        return;
    }
    const promise = fetchSource(track);
    prefetched.set(key, { promise, at: Date.now() });
    promise
        .then((source) => {
            if (source.kind === "audio") {
                warmAudio?.removeAttribute("src");
                warmAudio = new Audio();
                warmAudio.preload = "auto";
                warmAudio.muted = true;
                warmAudio.src = source.src;
            }
        })
        .catch(() => {
            prefetched.delete(key);
        });
}

export async function resolveSource(track: Track): Promise<PlaybackSource> {
    const key = sourceKey(track);
    const cached = prefetched.get(key);
    if (cached) {
        prefetched.delete(key);
        if (Date.now() - cached.at < PREFETCH_TTL_MS) {
            try {
                return await cached.promise;
            } catch {
            }
        }
    }
    return fetchSource(track);
}

async function fetchSource(track: Track): Promise<PlaybackSource> {
    if (track.audioUrl) {
        return { kind: "audio", src: track.audioUrl };
    }

    if (track.service === "local" && track.serviceId) {
        const url = await getUploadAudioUrl(Number(track.serviceId));
        return url
            ? { kind: "audio", src: url }
            : { kind: "unsupported", message: "Этот файл удалён из медиатеки" };
    }

    if (!track.service || !track.serviceId) {
        return { kind: "unsupported", message: "Это демо-трек — найдите музыку через поиск" };
    }

    const info = await fetchTrack(track.service, track.serviceId);

    const directUrl = info.direct_audio_url ?? info.playback?.direct_audio_url;
    if (directUrl) {
        return { kind: "audio", src: directUrl };
    }

    const playback = info.playback;
    if (playback?.kind === "audio_stream" || playback?.kind === "direct_url") {
        return { kind: "audio", src: info.stream_url ?? playback.ref };
    }
    if (playback?.kind === "youtube_iframe") {
        return { kind: "youtube", src: playback.ref };
    }
    if (playback?.kind === "soundcloud_widget") {
        return { kind: "soundcloud", src: playback.ref };
    }

    return {
        kind: "unsupported",
        message: "Этот трек нельзя проиграть прямо здесь",
        externalUrl: info.external_url ?? track.externalUrl,
    };
}

export function createEngine(kind: "audio" | "youtube" | "soundcloud", events: EngineEvents): PlayerEngine {
    if (kind === "youtube") {
        return createYouTubeEngine(events);
    }
    if (kind === "soundcloud") {
        return createSoundCloudEngine(events);
    }
    return createAudioEngine(events);
}
