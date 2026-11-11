import { LOAD_TIMEOUT, createHiddenBox, loadScript } from "./hiddenHost.ts";
import type { EngineEvents, PlayerEngine } from "./types.ts";

type SoundCloudWidget = {
    bind: (event: string, callback: (data: { currentPosition?: number }) => void) => void
    play: () => void
    pause: () => void
    seekTo: (milliseconds: number) => void
    setVolume: (volume: number) => void
    getDuration: (callback: (milliseconds: number) => void) => void
}

type SoundCloudApi = {
    Widget: ((iframe: HTMLIFrameElement) => SoundCloudWidget) & {
        Events: Record<"READY" | "PLAY" | "PAUSE" | "FINISH" | "PLAY_PROGRESS" | "ERROR", string>
    }
}

declare global {
    interface Window {
        SC?: SoundCloudApi
    }
}

export function createSoundCloudEngine(events: EngineEvents): PlayerEngine {
    let widget: SoundCloudWidget | null = null;
    let isReady = false;
    let wantsToPlay = false;
    let volume = 1;
    let duration = 0;
    let isDestroyed = false;
    let readyTimer: number | undefined;
    const box = createHiddenBox();

    return {
        async load(trackUrl) {
            await loadScript("https://w.soundcloud.com/player/api.js");
            const api = window.SC;
            if (isDestroyed || !api) {
                return;
            }

            const iframe = document.createElement("iframe");
            iframe.allow = "autoplay";
            iframe.src = "https://w.soundcloud.com/player/?url=" + encodeURIComponent(trackUrl)
                + "&auto_play=false&visual=false&show_comments=false";
            box.appendChild(iframe);

            const current = api.Widget(iframe);
            widget = current;
            const names = api.Widget.Events;

            readyTimer = setTimeout(() => {
                if (!isReady && !isDestroyed) {
                    events.onError("Плеер SoundCloud не отвечает");
                }
            }, LOAD_TIMEOUT);

            current.bind(names.READY, () => {
                isReady = true;
                clearTimeout(readyTimer);
                current.setVolume(volume * 100);
                current.getDuration((milliseconds) => {
                    duration = milliseconds / 1000;
                    events.onTime(0, duration);
                });
                if (wantsToPlay) {
                    current.play();
                }
            });
            current.bind(names.PLAY, () => !isDestroyed && events.onPlayingChange(true));
            current.bind(names.PAUSE, () => !isDestroyed && events.onPlayingChange(false));
            current.bind(names.FINISH, () => {
                if (!isDestroyed) {
                    events.onPlayingChange(false);
                    events.onEnded();
                }
            });
            current.bind(names.PLAY_PROGRESS, (data) => {
                if (!isDestroyed) {
                    events.onTime((data.currentPosition ?? 0) / 1000, duration);
                }
            });
            current.bind(names.ERROR, () => {
                if (!isDestroyed) {
                    events.onError("SoundCloud не разрешает проиграть этот трек здесь");
                }
            });
        },
        play() {
            wantsToPlay = true;
            if (widget && isReady) {
                widget.play();
            }
        },
        pause() {
            wantsToPlay = false;
            if (widget && isReady) {
                widget.pause();
            }
        },
        seek(seconds) {
            if (widget && isReady) {
                widget.seekTo(seconds * 1000);
            }
        },
        setVolume(newVolume) {
            volume = newVolume;
            if (widget && isReady) {
                widget.setVolume(newVolume * 100);
            }
        },
        destroy() {
            isDestroyed = true;
            clearTimeout(readyTimer);
            widget?.pause();
            box.remove();
        },
    };
}
