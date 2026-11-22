import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import Grain from "../entities/Grain.tsx";
import { formatTime } from "../shared/format.ts";
import { setTrackLiked } from "../shared/favorites.ts";
import { openAddToPlaylist } from "../shared/playlists.ts";
import { showToast } from "../shared/toast.ts";
import { getTrim, MIN_TRIM_LENGTH, saveTrim } from "../shared/player/trims.ts";
import CloseIcon from "../shared/icons/close.svg?react";
import PlusIcon from "../shared/icons/plus.svg?react";
import type { PlayerControls } from "../shared/player/usePlayer.ts";
import type { Service, Track } from "../shared/types.ts";
import HeartIcon from "../shared/icons/heart.svg?react";
import HeartFilledIcon from "../shared/icons/heart-filled.svg?react";
import ShuffleIcon from "../shared/icons/shuffle.svg?react";
import PrevIcon from "../shared/icons/prev.svg?react";
import PlayIcon from "../shared/icons/play.svg?react";
import PauseIcon from "../shared/icons/pause.svg?react";
import NextIcon from "../shared/icons/next.svg?react";
import RepeatIcon from "../shared/icons/repeat.svg?react";
import QueueIcon from "../shared/icons/queue.svg?react";
import VolumeIcon from "../shared/icons/volume.svg?react";
import VolumeOffIcon from "../shared/icons/volume-off.svg?react";
import EditorIcon from "../shared/icons/editor.svg?react";

type PlayerProps = {
    track: Track
    player: PlayerControls
    services: Service[]
    isQueueOpen: boolean
    onToggleQueue: () => void
}

function rangeStyle(value: number, max: number): CSSProperties {
    const percent = max > 0 ? Math.min(value / max, 1) * 100 : 0;
    return { "--fill": percent + "%" } as CSSProperties;
}

function Player({ track, player, services, isQueueOpen, onToggleQueue }: PlayerProps) {
    const [isLiked, setIsLiked] = useState(track.liked === true);
    const [dragTime, setDragTime] = useState<number | null>(null);
    const volumeBeforeMute = useRef(0.7);
    const isDragging = useRef(false);
    const dragValue = useRef(0);
    // Обрезка: черновик границ, пока открыт режим обрезки; null — режим закрыт
    const [trimDraft, setTrimDraft] = useState<{ start: number, end: number } | null>(null);
    // Закрытие с анимацией: элементы обрезки сначала плавно исчезают, потом убираются
    const [isTrimClosing, setIsTrimClosing] = useState(false);
    const closeTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
    // Плавный переход заливки включаем только на время смены режима — иначе она отставала бы от позиции
    const [fillAnimating, setFillAnimating] = useState(false);
    const fillTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

    function animateFill() {
        clearTimeout(fillTimer.current);
        setFillAnimating(true);
        fillTimer.current = setTimeout(() => setFillAnimating(false), 320);
    }

    useEffect(() => () => {
        clearTimeout(closeTimer.current);
        clearTimeout(fillTimer.current);
    }, []);

    // Пока открыта обрезка, плеер играет по текущим ручкам, а не по сохранённой обрезке
    const { setTrimPreview, setTrimHold } = player;
    useEffect(() => {
        setTrimPreview(trimDraft ?? undefined);
    }, [trimDraft, setTrimPreview]);
    useEffect(() => () => {
        setTrimPreview(undefined);
        setTrimHold(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    function holdWhileDragging() {
        setTrimHold(true);
        document.addEventListener("pointerup", () => setTrimHold(false), { once: true });
    }

    function closeTrim() {
        if (!trimDraft || isTrimClosing) {
            return;
        }
        setIsTrimClosing(true);
        animateFill();
        closeTimer.current = setTimeout(() => {
            setTrimDraft(null);
            setIsTrimClosing(false);
        }, 180);
    }
    const [savedTrim, setSavedTrim] = useState(() => getTrim(track));

    const service = services.find((item) => item.code === track.source);
    const sourceName = track.source === "ФАЙЛ" ? "Моя музыка" : service?.name ?? track.source;
    const time = Math.min(player.currentTime, player.duration || player.currentTime);
    const shownTime = dragTime ?? time;

    useEffect(() => {
        function handleKey(event: KeyboardEvent) {
            const target = event.target as HTMLElement;
            const isTyping = ["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(target.tagName) || target.isContentEditable;
            if (event.code === "Space" && !isTyping) {
                event.preventDefault();
                player.togglePlay();
            }
        }
        document.addEventListener("keydown", handleKey);
        return () => document.removeEventListener("keydown", handleKey);
    }, [player]);

    function startDrag() {
        isDragging.current = true;
        dragValue.current = time;
        setDragTime(time);
        document.addEventListener("pointerup", finishDrag, { once: true });
    }

    function finishDrag() {
        isDragging.current = false;
        player.seek(dragValue.current);
        setDragTime(null);
    }

    // Ползунок воспроизведения не выходит за кусок обрезки — и пока его тянут, и после
    function clampToTrim(value: number) {
        const range = trimDraft ?? savedTrim;
        if (!range) {
            return value;
        }
        return Math.min(Math.max(value, range.start), Math.max(range.start, range.end - 0.5));
    }

    function handleProgressChange(rawValue: number) {
        const value = clampToTrim(rawValue);
        if (isDragging.current) {
            dragValue.current = value;
            setDragTime(value);
        } else {
            player.seek(value);
        }
    }

    // Сохранённая обрезка вне режима обрезки: позиция и длина считаются внутри куска
    const pieceStart = savedTrim && player.duration > 0 ? savedTrim.start : 0;
    const pieceLength = savedTrim && player.duration > 0 ? Math.min(savedTrim.end, player.duration) - savedTrim.start : player.duration;
    const pieceTime = Math.min(Math.max(0, shownTime - pieceStart), pieceLength);

    // Геометрия тёмной заливки в процентах дорожки
    const isEditingTrim = trimDraft !== null && !isTrimClosing;
    const fillLeft = isEditingTrim && trimDraft ? trimDraft.start / player.duration * 100 : 0;
    const fillWidth = isEditingTrim && trimDraft
        ? (trimDraft.end - trimDraft.start) / player.duration * 100
        : pieceLength > 0 ? pieceTime / pieceLength * 100 : 0;

    // Позиция с учётом куска: пока трек не запускали, время плеера 0:00, но играть он начнёт с начала куска —
    // поэтому в редакторе кружок показываем там, откуда трек на самом деле заиграет
    const editTime = clampToTrim(shownTime);

    // Положение кружка позиции (0–1): в обрезке — по всему треку, иначе — внутри куска
    const thumbRatio = isEditingTrim
        ? (player.duration > 0 ? Math.min(1, Math.max(0, editTime / player.duration)) : 0)
        : (pieceLength > 0 ? pieceTime / pieceLength : 0);

    function openTrim() {
        if (player.duration <= 0) {
            showToast("Обрезать можно, когда трек загрузится");
            return;
        }
        // Если нажали во время закрытия — отменяем закрытие
        clearTimeout(closeTimer.current);
        setIsTrimClosing(false);
        animateFill();
        setTrimDraft(savedTrim ? { ...savedTrim } : { start: 0, end: player.duration });
    }

    function changeTrimStart(value: number) {
        if (!trimDraft) {
            return;
        }
        const start = Math.min(value, trimDraft.end - MIN_TRIM_LENGTH);
        setTrimDraft({ ...trimDraft, start: Math.max(0, start) });
    }

    function changeTrimEnd(value: number) {
        if (!trimDraft) {
            return;
        }
        const end = Math.max(value, trimDraft.start + MIN_TRIM_LENGTH);
        setTrimDraft({ ...trimDraft, end: Math.min(player.duration, end) });
    }

    function confirmTrim() {
        if (!trimDraft) {
            return;
        }
        try {
            saveTrim(track, trimDraft.start, trimDraft.end, player.duration);
            setSavedTrim(getTrim(track));
            const isWhole = trimDraft.start <= 0.5 && trimDraft.end >= player.duration - 0.5;
            if (!isWhole) {
                showToast("Трек обрезан: " + formatTime(Math.floor(trimDraft.start)) + " — " + formatTime(Math.floor(trimDraft.end)));
            }
            closeTrim();
        } catch (err) {
            showToast(err instanceof Error ? err.message : "Не удалось сохранить обрезку");
        }
    }

    function toggleLike() {
        const newValue = !isLiked;
        setIsLiked(newValue);
        setTrackLiked(track, newValue).catch(() => setIsLiked(!newValue));
    }

    function toggleMute() {
        if (player.volume > 0) {
            volumeBeforeMute.current = player.volume;
            player.setVolume(0);
        } else {
            player.setVolume(volumeBeforeMute.current || 0.7);
        }
    }

    const repeatTitle = player.repeat === "one" ? "Повтор трека включён" : "Повторять трек";

    return (
        <footer className={trimDraft ? "player trimming" : "player"}>
            <Grain/>

            <div className="player-track">
                <a href={track.externalUrl ?? "#"} target={track.externalUrl ? "_blank" : undefined} rel="noreferrer" title={"Открыть «" + track.title + "»"}>
                    <img className="player-cover" src={track.cover} alt=""/>
                </a>
                <div className="player-info">
                    <span className="player-title">{track.title}</span>
                    <span className="player-artist">{track.artist}</span>
                    {player.error ? (
                        <span className="player-error">
                            {player.error}
                            {player.externalUrl && (
                                <a href={player.externalUrl} target="_blank" rel="noreferrer">ОТКРЫТЬ</a>
                            )}
                        </span>
                    ) : (
                        <span className="player-source">
                            <span className="player-badge" title={"Играет из " + sourceName}>{track.source}</span>
                            {track.edited && <span className="player-badge">С ПРАВКАМИ</span>}
                            {savedTrim && (
                                <span
                                    className="player-badge player-badge-icon"
                                    title={"Обрезан: играет " + formatTime(Math.floor(savedTrim.start)) + " — " + formatTime(Math.floor(savedTrim.end))}
                                    aria-label="Трек обрезан"
                                >
                                    <EditorIcon width={12} height={12}/>
                                </span>
                            )}
                            {player.isLoading && <span className="player-badge">ЗАГРУЗКА…</span>}
                        </span>
                    )}
                </div>
                <button className="icon-button" title={isLiked ? "Убрать из избранного" : "В избранное"} onClick={toggleLike}>
                    {isLiked ? <HeartFilledIcon width={35} height={35}/> : <HeartIcon width={35} height={35}/>}
                </button>
                <button className="icon-button" title="Добавить в плейлист" onClick={() => openAddToPlaylist(track)}>
                    <PlusIcon width={24} height={24}/>
                </button>
            </div>

            <div className="player-center">
                <div className="player-controls">
                    {/* В волне порядок и так случайный — кнопку прячем, но оставляем место, чтобы кнопки не съезжали */}
                    <button
                        className={[
                            "icon-button mode",
                            player.isShuffle ? "active" : "",
                            player.isEndless ? "mode-hidden" : "",
                        ].filter(Boolean).join(" ")}
                        title={player.isShuffle ? "Перемешивание включено" : "Перемешать"}
                        aria-hidden={player.isEndless}
                        tabIndex={player.isEndless ? -1 : undefined}
                        disabled={player.isEndless}
                        onClick={player.toggleShuffle}
                    >
                        <ShuffleIcon/>
                    </button>
                    <button className="icon-button" title="Предыдущий трек" onClick={player.prev}>
                        <PrevIcon width={22} height={22}/>
                    </button>
                    <button
                        className={player.isLoading ? "icon-button big play-button loading" : "icon-button big play-button"}
                        title={player.isPlaying ? "Пауза" : "Играть"}
                        onClick={player.togglePlay}
                    >
                        {player.isPlaying ? <PauseIcon width={22} height={22}/> : <PlayIcon width={22} height={22}/>}
                    </button>
                    <button className="icon-button" title="Следующий трек" onClick={player.next} disabled={!player.hasNext}>
                        <NextIcon width={22} height={22}/>
                    </button>
                    <button
                        className={player.repeat !== "off" ? "icon-button mode active" : "icon-button mode"}
                        title={repeatTitle}
                        aria-pressed={player.repeat === "one"}
                        onClick={player.cycleRepeat}
                    >
                        <RepeatIcon/>
                    </button>
                </div>

                {/* Одна строка прогресса для обоих режимов: время слева и справа фиксированной ширины, а дорожка
                    с тёмной заливкой не пересоздаётся. Вне обрезки заливка — сыгранная часть, в обрезке — выбранный кусок;
                    при переключении она плавно перетекает из одного положения в другое */}
                <div className="progress-row">
                    <span className="progress-time">{formatTime(Math.floor(isEditingTrim && trimDraft ? trimDraft.start : pieceTime))}</span>
                    <div className={fillAnimating ? "progress-track animating" : "progress-track"}>
                        <span className="progress-rail"/>
                        <span className="progress-fill" style={{ left: fillLeft + "%", width: fillWidth + "%" }}/>
                        {/* Общий кружок позиции для обоих режимов — переезжает вместе с заливкой.
                            Встроенные кружки ползунков прозрачные и нужны только чтобы за них хвататься */}
                        <span
                            className={player.duration === 0 ? "progress-thumb disabled" : "progress-thumb"}
                            style={{ "--pos": thumbRatio } as CSSProperties}
                        />
                        {trimDraft ? (
                            <div className={isTrimClosing ? "trim-range closing" : "trim-range"}>
                                {/* Где сейчас играет трек: кружок можно тянуть, клик по дорожке перематывает */}
                                <input
                                    className="trim-position"
                                    type="range"
                                    min={0}
                                    max={player.duration}
                                    step={0.1}
                                    value={editTime}
                                    title={"Сейчас " + formatTime(Math.floor(editTime))}
                                    aria-label="Перемотка"
                                    onPointerDown={startDrag}
                                    onChange={(event) => handleProgressChange(Number(event.target.value))}
                                />
                                <input
                                    className="trim-handle"
                                    type="range"
                                    min={0}
                                    max={player.duration}
                                    step={0.1}
                                    value={trimDraft.start}
                                    aria-label="Начало обрезки"
                                    onPointerDown={holdWhileDragging}
                                    onChange={(event) => changeTrimStart(Number(event.target.value))}
                                />
                                <input
                                    className="trim-handle"
                                    type="range"
                                    min={0}
                                    max={player.duration}
                                    step={0.1}
                                    value={trimDraft.end}
                                    aria-label="Конец обрезки"
                                    onPointerDown={holdWhileDragging}
                                    onChange={(event) => changeTrimEnd(Number(event.target.value))}
                                />
                            </div>
                        ) : (
                            // Обрезанный трек выглядит как обычный, только короче: отсчёт идёт от начала куска
                            <input
                                className="range-input progress-input"
                                type="range"
                                min={0}
                                max={pieceLength || 0}
                                step={0.1}
                                value={pieceTime}
                                disabled={player.duration === 0}
                                title="Перемотка"
                                onPointerDown={startDrag}
                                onChange={(event) => handleProgressChange(Number(event.target.value) + pieceStart)}
                            />
                        )}
                    </div>
                    <span className="progress-time">{formatTime(Math.floor(isEditingTrim && trimDraft ? trimDraft.end : pieceLength))}</span>
                    {trimDraft && (
                        // Кнопки обрезки — сразу за временем конца, но вне потока: полоска не сжимается
                        <div className={isTrimClosing ? "trim-actions closing" : "trim-actions"}>
                            <button className="trim-button" title="Отменить" aria-label="Отменить обрезку" onClick={closeTrim}>
                                <CloseIcon width={16} height={16}/>
                            </button>
                            <button className="trim-button confirm" title="Сохранить обрезку" aria-label="Сохранить обрезку" onClick={confirmTrim}>
                                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                                    <path d="M5 12.5l4.5 4.5L19 7.5"/>
                                </svg>
                            </button>
                        </div>
                    )}
                </div>

            </div>

            <div className="player-right">
                <button
                    className={trimDraft || savedTrim ? "icon-button trim-toggle active" : "icon-button trim-toggle"}
                    title={trimDraft ? "Отменить редактирование" : "Обрезать трек"}
                    aria-pressed={trimDraft !== null}
                    onClick={() => (trimDraft && !isTrimClosing ? closeTrim() : openTrim())}
                >
                    <EditorIcon/>
                </button>
                <button
                    className={isQueueOpen ? "icon-button queue-toggle active" : "icon-button queue-toggle"}
                    title="Очередь"
                    aria-expanded={isQueueOpen}
                    onClick={onToggleQueue}
                >
                    <QueueIcon/>
                </button>
                <button className="icon-button volume-toggle" title={player.volume > 0 ? "Выключить звук" : "Включить звук"} onClick={toggleMute}>
                    {player.volume > 0 ? <VolumeIcon/> : <VolumeOffIcon/>}
                </button>
                <input
                    className="range-input volume-input"
                    type="range"
                    min={0}
                    max={1}
                    step={0.01}
                    value={player.volume}
                    style={rangeStyle(player.volume, 1)}
                    title="Громкость"
                    onChange={(event) => player.setVolume(Number(event.target.value))}
                />
            </div>
        </footer>
    )
}

export default Player
