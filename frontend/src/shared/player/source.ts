import { fetchTrack } from "../api.ts";
import type { Track } from "../types.ts";
import { createAudioEngine } from "./audioEngine.ts";
import { createSoundCloudEngine } from "./soundcloudEngine.ts";
import { createYouTubeEngine } from "./youtubeEngine.ts";
import type { EngineEvents, PlaybackSource, PlayerEngine } from "./types.ts";

export async function resolveSource(track: Track): Promise<PlaybackSource> {
    if (track.audioUrl) {
        return { kind: "audio", src: track.audioUrl };
    }

    if (!track.service || !track.serviceId) {
        return { kind: "unsupported", message: "Это демо-трек — найдите музыку через поиск" };
    }

    const info = await fetchTrack(track.service, track.serviceId);

    if (info.direct_audio_url) {
        return { kind: "audio", src: info.direct_audio_url };
    }

    const playback = info.playback;
    if (playback?.kind === "audio_stream") {
        return { kind: "audio", src: playback.ref };
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
