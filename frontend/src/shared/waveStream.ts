import type { Track } from "./types.ts";
import { getTrackKey } from "./favorites.ts";

export function seededShuffle<T>(items: T[], seedText: string) {
    let seed = 0;
    for (let i = 0; i < seedText.length; i++) {
        seed = (seed * 31 + seedText.charCodeAt(i)) >>> 0;
    }
    const random = () => {
        seed = (seed * 1664525 + 1013904223) >>> 0;
        return seed / 4294967296;
    };
    const result = [...items];
    for (let i = result.length - 1; i > 0; i--) {
        const j = Math.floor(random() * (i + 1));
        [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
}

export function createWaveStream(tracks: Track[], seed: string, recentTracks: Track[] = []) {
    let round = 0;
    let order = [...tracks];
    let cursor = 0;
    const avoidCount = Math.min(3, Math.max(0, tracks.length - 1));
    const recentKeys: string[] = avoidCount > 0 ? recentTracks.map(getTrackKey).slice(-avoidCount) : [];
    if (recentKeys.length > 0) {
        nextRound();
    }

    function nextRound() {
        round += 1;
        const shuffled = seededShuffle(tracks, seed + ":" + round);
        const fresh = shuffled.filter((track) => !recentKeys.includes(getTrackKey(track)));
        const repeated = shuffled.filter((track) => recentKeys.includes(getTrackKey(track)));
        order = [...fresh, ...repeated];
        cursor = 0;
    }

    function take(count: number): Track[] {
        const result: Track[] = [];
        if (tracks.length === 0) {
            return result;
        }
        while (result.length < count) {
            if (cursor >= order.length) {
                nextRound();
            }
            const track = order[cursor];
            cursor += 1;
            result.push(track);
            recentKeys.push(getTrackKey(track));
            while (recentKeys.length > avoidCount) {
                recentKeys.shift();
            }
        }
        return result;
    }

    return { take, canRepeat: tracks.length > 1 };
}
