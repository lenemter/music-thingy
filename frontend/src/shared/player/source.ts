import { fetchTrack } from "../api.ts";
import { getUploadAudioUrl } from "../library.ts";
import type { Track } from "../types.ts";
import { createAudioEngine } from "./audioEngine.ts";
import { createSoundCloudEngine } from "./soundcloudEngine.ts";
import { createYouTubeEngine } from "./youtubeEngine.ts";
import type { EngineEvents, PlaybackSource, PlayerEngine } from "./types.ts";

export async function resolveSource(track: Track): Promise<PlaybackSource> {
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
