import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import Grain from "../entities/Grain.tsx";
import { formatTime } from "../shared/format.ts";
import { setTrackLiked } from "../shared/favorites.ts";
import { openAddToPlaylist } from "../shared/playlists.ts";
import { showToast } from "../shared/toast.ts";
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

    function handleProgressChange(value: number) {
        if (isDragging.current) {
            dragValue.current = value;
            setDragTime(value);
        } else {
            player.seek(value);
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
        <footer className="player">
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

                <div className="progress-row">
                    <span>{formatTime(Math.floor(shownTime))}</span>
                    <input
                        className="range-input progress-input"
                        type="range"
                        min={0}
                        max={player.duration || 0}
                        step={0.1}
                        value={shownTime}
                        style={rangeStyle(shownTime, player.duration)}
                        disabled={player.duration === 0}
                        title="Перемотка"
                        onPointerDown={startDrag}
                        onChange={(event) => handleProgressChange(Number(event.target.value))}
                    />
                    <span>{formatTime(Math.floor(player.duration))}</span>
                </div>
            </div>

            <div className="player-right">
                <button className="icon-button" title="Редактор" onClick={() => showToast("Раздел в разработке")}><EditorIcon/></button>
                <button
                    className={isQueueOpen ? "icon-button queue-toggle active" : "icon-button queue-toggle"}
                    title="Очередь"
                    aria-expanded={isQueueOpen}
                    onClick={onToggleQueue}
                >
                    <QueueIcon/>
                </button>
                <button className="icon-button" title={player.volume > 0 ? "Выключить звук" : "Включить звук"} onClick={toggleMute}>
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
