import type { EngineEvents, PlayerEngine } from "./types.ts";

export function createAudioEngine(events: EngineEvents): PlayerEngine {
    const audio = new Audio();
    audio.preload = "auto";
    let isDestroyed = false;

    function sendTime() {
        if (!isDestroyed) {
            events.onTime(audio.currentTime, Number.isFinite(audio.duration) ? audio.duration : 0);
        }
    }

    audio.addEventListener("timeupdate", sendTime);
    audio.addEventListener("durationchange", sendTime);
    audio.addEventListener("play", () => !isDestroyed && events.onPlayingChange(true));
    audio.addEventListener("pause", () => !isDestroyed && events.onPlayingChange(false));
    audio.addEventListener("ended", () => !isDestroyed && events.onEnded());
    audio.addEventListener("error", () => !isDestroyed && events.onError("Не удалось загрузить аудио"));

    return {
        async load(src) {
            audio.src = src;
            audio.load();
        },
        play() {
            audio.play().catch(() => {
                if (!isDestroyed) {
                    events.onPlayingChange(false);
                }
            });
        },
        pause() {
            audio.pause();
        },
        seek(seconds) {
            audio.currentTime = seconds;
        },
        setVolume(volume) {
            audio.volume = volume;
        },
        destroy() {
            isDestroyed = true;
            audio.pause();
            audio.removeAttribute("src");
            audio.load();
        },
    };
}
