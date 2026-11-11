import { addFavoriteTrack, recordListeningHistory, removeFavoriteTrack } from "./api.ts";
import type { Track } from "./types.ts";

export async function setTrackLiked(track: Track, liked: boolean) {
    if (!track.service || !track.serviceId) {
        return;
    }
    if (liked) {
        await addFavoriteTrack({ ...track, service_id: track.serviceId });
    } else {
        await removeFavoriteTrack(track.service, track.serviceId);
    }
}

export function saveToHistory(track: Track) {
    if (!track.service || !track.serviceId) {
        return;
    }
    recordListeningHistory({ ...track, service_id: track.serviceId }).catch(() => {});
}
