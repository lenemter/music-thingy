import { useEffect, useRef, useState } from "react";
import type { Track } from "../types.ts";
import { createEngine, resolveSource } from "./source.ts";
import { getTrim } from "./trims.ts";
import type { Trim } from "./trims.ts";
import type { EngineEvents, PlayerEngine } from "./types.ts";

// Повтор: выключен или повтор текущего трека, когда он закончится
export type RepeatMode = "off" | "one"

// Сколько треков держать впереди в бесконечной очереди
const UPCOMING_COUNT = 3;

// Плавное нарастание и затухание громкости на границах обрезки
const TRIM_FADE_SECONDS = 1.5;
const FADE_TICK_MS = 50;

function shuffleTracks(tracks: Track[]) {
    const result = [...tracks];
    for (let i = result.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
}

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

export function usePlayer(initialQueue: Track[], initialIndex = 0) {
    const [queue, setQueue] = useState(initialQueue);
    const [index, setIndex] = useState(initialIndex);
    const [isPlaying, setIsPlaying] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(initialQueue[initialIndex]?.duration ?? 0);
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
    // Источник, который подкладывает треки в конец очереди (бесконечная волна)
    const extendRef = useRef<((count: number) => Track[]) | null>(null);
    // Порядок очереди до перемешивания — чтобы вернуть его, когда перемешивание выключат
    const originalOrderRef = useRef<Track[]>(initialQueue);
    // Обрезка, которую сейчас редактируют в плеере (undefined — не редактируют, null — без обрезки).
    // Пока она задана, плеер слушается её, а не сохранённой.
    const trimPreviewRef = useRef<Trim | null | undefined>(undefined);
    // Пока тянут ручку обрезки, позицию воспроизведения не трогаем
    const trimHoldRef = useRef(false);

    function effectiveTrim(track: Track | undefined): Trim | null {
        return trimPreviewRef.current !== undefined ? trimPreviewRef.current : getTrim(track);
    }

    // Последнее известное время трека и когда оно пришло — по ним каждые 50 мс оцениваем позицию для затухания
    const lastTimeRef = useRef({ time: 0, stamp: 0, total: 0 });
    const fadeTimerRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

    function seekEngine(seconds: number) {
        lastTimeRef.current = { ...lastTimeRef.current, time: seconds, stamp: performance.now() };
        pendingSeekRef.current = { target: seconds, until: Date.now() + 1500 };
        engineRef.current?.seek(seconds);
        setCurrentTime(seconds);
    }

    function withUpcoming(list: Track[], trackIndex: number) {
        const extend = extendRef.current;
        const upcoming = list.length - trackIndex - 1;
        if (!extend || upcoming >= UPCOMING_COUNT) {
            return list;
        }
        return [...list, ...extend(UPCOMING_COUNT - upcoming)];
    }

    const currentTrack: Track | undefined = queue[index];

    async function startTrack(sourceList: Track[], trackIndex: number) {
        const list = withUpcoming(sourceList, trackIndex);
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

        // Обрезанный трек заканчивается на конце обрезки; флаг — чтобы не сработать дважды подряд
        let trimEndFired = false;
        let isEnginePlaying = false;
        let appliedVolume = -1;

        // Громкость на обрезанных краях: нарастает от начала куска и затихает к его концу.
        // Края, которые не обрезаны (начало трека, конец трека), не трогаем.
        clearInterval(fadeTimerRef.current);
        lastTimeRef.current = { time: 0, stamp: performance.now(), total: track.duration };
        fadeTimerRef.current = setInterval(() => {
            const engine = engineRef.current;
            if (!isActual()) {
                return;
            }
            if (!engine) {
                return;
            }
            let factor = 1;
            const trim = effectiveTrim(track);
            const last = lastTimeRef.current;
            if (trim && isEnginePlaying && !trimHoldRef.current) {
                const now = last.time + (performance.now() - last.stamp) / 1000;
                const fade = Math.min(TRIM_FADE_SECONDS, (trim.end - trim.start) / 4);
                if (trim.start > 0.05) {
                    factor = Math.min(factor, Math.max(0, Math.min(1, (now - trim.start) / fade)));
                }
                if (last.total > 0 && trim.end < last.total - 0.05) {
                    factor = Math.min(factor, Math.max(0, Math.min(1, (trim.end - now) / fade)));
                }
            }
            const volume = volumeRef.current * factor;
            if (Math.abs(volume - appliedVolume) > 0.003) {
                appliedVolume = volume;
                engine.setVolume(volume);
            }
        }, FADE_TICK_MS);

        const events: EngineEvents = {
            onTime: (time, total) => {
                if (isActual()) {
                    const pending = pendingSeekRef.current;
                    if (pending && Date.now() < pending.until && Math.abs(time - pending.target) > 1) {
                        return;
                    }
                    pendingSeekRef.current = null;
                    lastTimeRef.current = { time, stamp: performance.now(), total: total > 0 ? total : lastTimeRef.current.total };
                    setCurrentTime(time);
                    if (total > 0) {
                        setDuration(total);
                    }
                    const trim = effectiveTrim(track);
                    if (!trim || trimHoldRef.current) {
                        trimEndFired = false;
                    } else if (time >= trim.end) {
                        if (!trimEndFired) {
                            trimEndFired = true;
                            if (trimPreviewRef.current !== undefined) {
                                // Во время обрезки кусок играет по кругу, чтобы его можно было послушать
                                seekEngine(trim.start);
                            } else {
                                // Конец куска = конец трека: останавливаем звук и возвращаемся к началу куска,
                                // иначе без следующего трека звук продолжил бы играть в отрезанной части
                                engineRef.current?.pause();
                                seekEngine(trim.start);
                                endedRef.current();
                            }
                        }
                    } else if (time < trim.start - 0.5) {
                        // Каким-то образом оказались в отрезанном начале — переходим к началу куска
                        seekEngine(trim.start);
                    } else {
                        trimEndFired = false;
                    }
                }
            },
            onPlayingChange: (playing) => {
                if (isActual()) {
                    isEnginePlaying = playing;
                    lastTimeRef.current = { ...lastTimeRef.current, stamp: performance.now() };
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
            const trim = effectiveTrim(track);
            if (trim && trim.start > 0) {
                pendingSeekRef.current = { target: trim.start, until: Date.now() + 1500 };
                lastTimeRef.current = { ...lastTimeRef.current, time: trim.start, stamp: performance.now() };
                engine.seek(trim.start);
                setCurrentTime(trim.start);
                // начало обрезано — стартуем с тишины, дальше громкость нарастает
                engine.setVolume(0);
                appliedVolume = 0;
            }
            engine.play();
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
        // Перемешивание меняет порядок самой очереди, поэтому следующий трек — всегда следующий в списке
        if (index + 1 < queue.length) {
            return index + 1;
        }
        return null;
    }

    function playTrack(track: Track, list: Track[], extend?: (count: number) => Track[]) {
        // Новый бесконечный источник (волна) всегда перезапускает очередь, даже если трек тот же
        if (!extend && currentTrack && track.id === currentTrack.id && engineRef.current) {
            togglePlay();
            return;
        }

        extendRef.current = extend ?? null;
        originalOrderRef.current = list;
        const trackIndex = list.findIndex((item) => item.id === track.id);
        if (trackIndex === -1) {
            startTrack([track], 0);
        } else if (isShuffle && !extend) {
            // Перемешивание включено: выбранный трек первым, остальные — в случайном порядке
            startTrack([track, ...shuffleTracks(list.filter((_, i) => i !== trackIndex))], 0);
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

    // Перемотка не заходит в отрезанные части трека
    function seek(seconds: number) {
        const trim = effectiveTrim(currentTrack);
        const target = trim ? Math.min(Math.max(seconds, trim.start), Math.max(trim.start, trim.end - 0.5)) : seconds;
        seekEngine(target);
    }

    function setTrimPreview(trim: Trim | null | undefined) {
        trimPreviewRef.current = trim;
    }

    // Пока ручку тянут, позицию не трогаем. Когда отпустили и позиция оказалась в отрезанной зоне,
    // ближайшее обновление времени переведёт её к началу куска (см. onTime)
    function setTrimHold(isHeld: boolean) {
        trimHoldRef.current = isHeld;
    }

    function next() {
        const nextIndex = getNextIndex();
        if (nextIndex !== null) {
            startTrack(queue, nextIndex);
        }
    }

    // Начало трека с учётом обрезки
    function trackStart() {
        return effectiveTrim(currentTrack)?.start ?? 0;
    }

    function prev() {
        if (currentTime > trackStart() + 3 || queue.length < 2) {
            seek(trackStart());
        } else if (index > 0) {
            startTrack(queue, index - 1);
        } else {
            seek(trackStart());
        }
    }

    function handleEnded() {
        if (repeat === "one") {
            seek(trackStart());
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

    // Очередь: переход к треку, удаление и очистка без перезапуска текущего трека
    function playAt(trackIndex: number) {
        if (trackIndex === index && engineRef.current) {
            togglePlay();
            return;
        }
        if (queue[trackIndex]) {
            startTrack(queue, trackIndex);
        }
    }

    function removeAt(trackIndex: number) {
        if (trackIndex === index || !queue[trackIndex]) {
            return;
        }
        const newIndex = trackIndex < index ? index - 1 : index;
        setQueue(withUpcoming(queue.filter((_, i) => i !== trackIndex), newIndex));
        setIndex(newIndex);
    }

    // Подключить бесконечный источник к уже собранной очереди (восстановление волны после перезагрузки)
    function setExtend(extend: ((count: number) => Track[]) | null) {
        extendRef.current = extend;
        if (extend) {
            setQueue(withUpcoming(queue, index));
        }
    }

    function clearUpcoming() {
        setQueue(withUpcoming(queue.slice(0, index + 1), index));
    }

    function setVolume(newVolume: number) {
        volumeRef.current = newVolume;
        setVolumeState(newVolume);
        engineRef.current?.setVolume(newVolume);
        saveVolume(newVolume);
    }

    function toggleShuffle() {
        const played = queue.slice(0, index + 1);
        const upcoming = queue.slice(index + 1);
        if (!isShuffle) {
            originalOrderRef.current = queue;
            setQueue([...played, ...shuffleTracks(upcoming)]);
        } else {
            // Возвращаем исходный порядок для того, что ещё не сыграло
            const original = originalOrderRef.current;
            const ordered = original.filter((track) => upcoming.includes(track));
            const extra = upcoming.filter((track) => !original.includes(track));
            setQueue([...played, ...ordered, ...extra]);
        }
        setIsShuffle(!isShuffle);
    }

    function cycleRepeat() {
        setRepeat(repeat === "off" ? "one" : "off");
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
        return () => {
            clearInterval(fadeTimerRef.current);
            engineRef.current?.destroy();
        };
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
        queue,
        index,
        isEndless: extendRef.current !== null,
        setExtend,
        setTrimPreview,
        setTrimHold,
        playAt,
        removeAt,
        clearUpcoming,
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
