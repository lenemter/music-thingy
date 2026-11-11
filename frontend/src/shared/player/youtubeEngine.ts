import { LOAD_TIMEOUT, createHiddenBox, loadScript, withTimeout } from "./hiddenHost.ts";
import type { EngineEvents, PlayerEngine } from "./types.ts";

type YouTubePlayer = {
    playVideo: () => void
    pauseVideo: () => void
    seekTo: (seconds: number, allowSeekAhead: boolean) => void
    setVolume: (volume: number) => void
    getCurrentTime: () => number
    getDuration: () => number
    destroy: () => void
}

type YouTubeApi = {
    Player: new (element: HTMLElement, options: object) => YouTubePlayer
}

declare global {
    interface Window {
        YT?: YouTubeApi
        onYouTubeIframeAPIReady?: () => void
    }
}

let apiReady: Promise<YouTubeApi> | null = null;

function loadYouTubeApi() {
    if (apiReady === null) {
        const loading = new Promise<YouTubeApi>((resolve, reject) => {
            if (window.YT?.Player) {
                resolve(window.YT);
                return;
            }
            window.onYouTubeIframeAPIReady = () => resolve(window.YT as YouTubeApi);
            loadScript("https://www.youtube.com/iframe_api").catch(reject);
        });
        apiReady = withTimeout(loading, "Плеер YouTube не отвечает");
        apiReady.catch(() => {
            apiReady = null;
        });
    }
    return apiReady;
}

export function createYouTubeEngine(events: EngineEvents): PlayerEngine {
    let player: YouTubePlayer | null = null;
    let isReady = false;
    let wantsToPlay = false;
    let volume = 1;
    let isDestroyed = false;
    let timer: number | undefined;
    let readyTimer: number | undefined;
    const box = createHiddenBox();

    function sendTime() {
        if (player && isReady && !isDestroyed) {
            events.onTime(player.getCurrentTime(), player.getDuration());
        }
    }

    return {
        async load(videoId) {
            const api = await loadYouTubeApi();
            if (isDestroyed) {
                return;
            }

            const element = document.createElement("div");
            box.appendChild(element);

            player = new api.Player(element, {
                videoId: videoId,
                width: 200,
                height: 200,
                playerVars: { autoplay: 0, controls: 0, playsinline: 1, disablekb: 1 },
                events: {
                    onReady: () => {
                        isReady = true;
                        clearTimeout(readyTimer);
                        player?.setVolume(volume * 100);
                        if (wantsToPlay) {
                            player?.playVideo();
                        }
                    },
                    onStateChange: (event: { data: number }) => {
                        if (isDestroyed) {
                            return;
                        }
                        if (event.data === 1) {
                            events.onPlayingChange(true);
                        }
                        if (event.data === 2) {
                            events.onPlayingChange(false);
                        }
                        if (event.data === 0) {
                            events.onPlayingChange(false);
                            events.onEnded();
                        }
                    },
                    onError: () => {
                        if (!isDestroyed) {
                            events.onError("YouTube не разрешает проиграть это видео здесь");
                        }
                    },
                },
            });

            timer = setInterval(sendTime, 250);
            readyTimer = setTimeout(() => {
                if (!isReady && !isDestroyed) {
                    events.onError("Плеер YouTube не отвечает");
                }
            }, LOAD_TIMEOUT);
        },
        play() {
            wantsToPlay = true;
            if (player && isReady) {
                player.playVideo();
            }
        },
        pause() {
            wantsToPlay = false;
            if (player && isReady) {
                player.pauseVideo();
            }
        },
        seek(seconds) {
            if (player && isReady) {
                player.seekTo(seconds, true);
            }
        },
        setVolume(newVolume) {
            volume = newVolume;
            if (player && isReady) {
                player.setVolume(newVolume * 100);
            }
        },
        destroy() {
            isDestroyed = true;
            clearInterval(timer);
            clearTimeout(readyTimer);
            player?.destroy();
            box.remove();
        },
    };
}
