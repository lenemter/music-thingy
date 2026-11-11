import type { Track, UserFile } from "../types.ts";
import type { TrackRead } from "./types.ts";
import { getServiceName } from "./services.ts";
import { getOverride } from "../library.ts";
import { coverUrl, fallbackCover } from "../coverTemplates.ts";

function getArtist(item: TrackRead) {
    if (item.artist && item.artist.trim() !== "") {
        return item.artist;
    }
    if (item.service === "youtube" && item.title.includes(" - ")) {
        return item.title.split(" - ")[0].trim();
    }
    return getServiceName(item.service);
}

export function trackFromRead(item: TrackRead): Track {
    const override = item.service === "local" ? getOverride(item.service_id) : undefined;
    const cover = override?.cover === null ? "" : coverUrl(override?.cover ?? item.cover);

    return {
        id: item.track_key ?? item.service + ":" + item.service_id,
        title: override?.title ?? item.title,
        artist: override?.artist ?? getArtist(item),
        cover: cover || fallbackCover(item.service_id),
        duration: item.duration,
        sources: item.sources.length > 0 ? item.sources : [item.source],
        source: item.source,
        edited: item.edited,
        liked: item.liked,
        service: item.service,
        serviceId: item.service_id,
        audioUrl: item.direct_audio_url ?? undefined,
        externalUrl: item.external_url ?? undefined,
    };
}

export function trackFromFile(file: UserFile): Track {
    return {
        id: "local:" + file.id,
        title: file.name,
        artist: file.artist,
        cover: file.cover || fallbackCover(file.id),
        duration: file.duration,
        sources: ["ФАЙЛ"],
        source: "ФАЙЛ",
        edited: file.isEdited,
        service: "local",
        serviceId: String(file.id),
        audioUrl: file.audioUrl,
    };
}
