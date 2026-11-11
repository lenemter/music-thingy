import { useEffect, useRef, useState } from "react";
import type { Track } from "../types.ts";
import { saveToHistory } from "../favorites.ts";
import { createEngine, resolveSource } from "./source.ts";
import type { EngineEvents, PlayerEngine } from "./types.ts";

export type RepeatMode = "off" | "all" | "one"

const VOLUME_KEY = "signal-volume";

function loadVolume() {
    try {
        const text = localStorage.getItem(VOLUME_KEY);
        const value = Number(text);
        if (text !== null && value >= 0 && value <= 1) {
            return value;
        }
    } catch {
        return 0.7;
    }
    return 0.7;
}

function saveVolume(volume: number) {
    try {
        localStorage.setItem(VOLUME_KEY, String(volume));
    } catch {
        return;
    }
}

export function usePlayer(initialQueue: Track[]) {
    const [queue, setQueue] = useState(initialQueue);
    const [index, setIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(initialQueue[0]?.duration ?? 0);
    const [volume, setVolumeState] = useState(loadVolume);
    const [isShuffle, setIsShuffle] = useState(false);
    const [repeat, setRepeat] = useState<RepeatMode>("off");
    const [error, setError] = useState("");
    const [externalUrl, setExternalUrl] = useState<string | undefined>(undefined);

    const engineRef = useRef<PlayerEngine | null>(null);
    const loadIdRef = useRef(0);
    const volumeRef = useRef(volume);
    const endedRef = useRef<() => void>(() => {});
    const pendingSeekRef = useRef<{ target: number, until: number } | null>(null);

    const currentTrack: Track | undefined = queue[index];

    async function startTrack(list: Track[], trackIndex: number) {
        const track = list[trackIndex];
        const loadId = loadIdRef.current + 1;
        loadIdRef.current = loadId;
        const isActual = () => loadIdRef.current === loadId;

        engineRef.current?.destroy();
        engineRef.current = null;

        setQueue(list);
        setIndex(trackIndex);
        setCurrentTime(0);
        setDuration(track.duration);
        setIsPlaying(false);
        setError("");
        setExternalUrl(undefined);
        setIsLoading(true);

        const events: EngineEvents = {
            onTime: (time, total) => {
                if (isActual()) {
                    const pending = pendingSeekRef.current;
                    if (pending && Date.now() < pending.until && Math.abs(time - pending.target) > 1) {
                        return;
                    }
                    pendingSeekRef.current = null;
                    setCurrentTime(time);
                    if (total > 0) {
                        setDuration(total);
                    }
                }
            },
            onPlayingChange: (playing) => {
                if (isActual()) {
                    setIsPlaying(playing);
                    setIsLoading(false);
                }
            },
            onEnded: () => {
                if (isActual()) {
                    endedRef.current();
                }
            },
            onError: (message) => {
                if (isActual()) {
                    setError(message);
                    setExternalUrl(track.externalUrl);
                    setIsPlaying(false);
                    setIsLoading(false);
                }
            },
        };

        try {
            const source = await resolveSource(track);
            if (!isActual()) {
                return;
            }

            if (source.kind === "unsupported") {
                setError(source.message);
                setExternalUrl(source.externalUrl);
                setIsLoading(false);
                return;
            }

            const engine = createEngine(source.kind, events);
            engineRef.current = engine;
            engine.setVolume(volumeRef.current);
            await engine.load(source.src);
            if (!isActual()) {
                return;
            }

            setIsLoading(false);
            engine.play();
            saveToHistory(track);
        } catch (err) {
            if (isActual()) {
                setError(err instanceof Error ? err.message : "Не удалось включить трек");
                setIsLoading(false);
            }
        }
    }

    function getNextIndex() {
        if (queue.length === 0) {
            return null;
        }
        if (isShuffle && queue.length > 1) {
            let nextIndex = index;
            while (nextIndex === index) {
                nextIndex = Math.floor(Math.random() * queue.length);
            }
            return nextIndex;
        }
        if (index + 1 < queue.length) {
            return index + 1;
        }
        return repeat === "all" ? 0 : null;
    }

    function playTrack(track: Track, list: Track[]) {
        if (currentTrack && track.id === currentTrack.id && engineRef.current) {
            togglePlay();
            return;
        }

        const trackIndex = list.findIndex((item) => item.id === track.id);
        if (trackIndex === -1) {
            startTrack([track], 0);
        } else {
            startTrack(list, trackIndex);
        }
    }

    function togglePlay() {
        const engine = engineRef.current;
        if (engine === null) {
            if (!isLoading && currentTrack) {
                startTrack(queue, index);
            }
            return;
        }
        if (isPlaying) {
            engine.pause();
        } else {
            engine.play();
        }
    }

    function seek(seconds: number) {
        pendingSeekRef.current = { target: seconds, until: Date.now() + 1500 };
        engineRef.current?.seek(seconds);
        setCurrentTime(seconds);
    }

    function next() {
        const nextIndex = getNextIndex();
        if (nextIndex !== null) {
            startTrack(queue, nextIndex);
        }
    }

    function prev() {
        if (currentTime > 3 || queue.length < 2) {
            seek(0);
        } else if (index > 0) {
            startTrack(queue, index - 1);
        } else if (repeat === "all") {
            startTrack(queue, queue.length - 1);
        } else {
            seek(0);
        }
    }

    function handleEnded() {
        if (repeat === "one") {
            seek(0);
            engineRef.current?.play();
            return;
        }
        const nextIndex = getNextIndex();
        if (nextIndex === null) {
            setIsPlaying(false);
            return;
        }
        startTrack(queue, nextIndex);
    }

    function setVolume(newVolume: number) {
        volumeRef.current = newVolume;
        setVolumeState(newVolume);
        engineRef.current?.setVolume(newVolume);
        saveVolume(newVolume);
    }

    function toggleShuffle() {
        setIsShuffle(!isShuffle);
    }

    function cycleRepeat() {
        if (repeat === "off") {
            setRepeat("all");
        } else if (repeat === "all") {
            setRepeat("one");
        } else {
            setRepeat("off");
        }
    }

    function stop() {
        loadIdRef.current += 1;
        engineRef.current?.destroy();
        engineRef.current = null;
        setIsPlaying(false);
        setIsLoading(false);
        setCurrentTime(0);
        if ("mediaSession" in navigator) {
            navigator.mediaSession.metadata = null;
        }
    }

    useEffect(() => {
        endedRef.current = handleEnded;

        if ("mediaSession" in navigator) {
            navigator.mediaSession.setActionHandler("play", togglePlay);
            navigator.mediaSession.setActionHandler("pause", togglePlay);
            navigator.mediaSession.setActionHandler("nexttrack", next);
            navigator.mediaSession.setActionHandler("previoustrack", prev);
        }
    });

    useEffect(() => {
        if (!("mediaSession" in navigator) || !currentTrack) {
            return;
        }
        navigator.mediaSession.metadata = new MediaMetadata({
            title: currentTrack.title,
            artist: currentTrack.artist,
            artwork: [{ src: currentTrack.cover }],
        });
    }, [currentTrack]);

    useEffect(() => {
        if ("mediaSession" in navigator) {
            navigator.mediaSession.playbackState = isPlaying ? "playing" : "paused";
        }
    }, [isPlaying]);

    useEffect(() => {
        return () => engineRef.current?.destroy();
    }, []);

    return {
        currentTrack,
        isPlaying,
        isLoading,
        currentTime,
        duration,
        volume,
        isShuffle,
        repeat,
        error,
        externalUrl,
        hasNext: getNextIndex() !== null,
        playTrack,
        togglePlay,
        seek,
        next,
        prev,
        setVolume,
        toggleShuffle,
        cycleRepeat,
        stop,
    };
}

export type PlayerControls = ReturnType<typeof usePlayer>
