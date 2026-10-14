import { useState } from "react";
import Grain from "../entities/Grain.tsx";
import { formatTime } from "../shared/format.ts";
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
import EditorIcon from "../shared/icons/editor.svg?react";

type PlayerProps = {
    track: Track
    currentTime: number
    services: Service[]
}

function Player({ track, currentTime, services }: PlayerProps) {
    const [isPlaying, setIsPlaying] = useState(true);
    const [isLiked, setIsLiked] = useState(track.liked === true);

    const service = services.find((item) => item.code === track.source);
    const progress = currentTime / track.duration * 100;

    return (
        <footer className="player">
            <Grain/>

            <div className="player-track">
                <a href="#" title={"Открыть «" + track.title + "»"}>
                    <img className="player-cover" src={track.cover} alt=""/>
                </a>
                <div className="player-info">
                    <span className="player-title">{track.title}</span>
                    <span className="player-artist">{track.artist}</span>
                    <span className="player-source">
                        <span className="player-badge" title={"Играет из " + service?.name}>{track.source}</span>
                        {track.edited && <span className="player-badge">С ПРАВКАМИ</span>}
                    </span>
                </div>
                <button className="icon-button" title={isLiked ? "Убрать из избранного" : "В избранное"} onClick={() => setIsLiked(!isLiked)}>
                    {isLiked ? <HeartFilledIcon width={35} height={35}/> : <HeartIcon width={35} height={35}/>}
                </button>
            </div>

            <div className="player-center">
                <div className="player-controls">
                    <button className="icon-button" title="Перемешать"><ShuffleIcon/></button>
                    <button className="icon-button" title="Предыдущий трек"><PrevIcon width={22} height={22}/></button>
                    <button
                        className="icon-button big play-button"
                        title={isPlaying ? "Пауза" : "Играть"}
                        onClick={() => setIsPlaying(!isPlaying)}
                    >
                        {isPlaying ? <PauseIcon width={22} height={22}/> : <PlayIcon width={22} height={22}/>}
                    </button>
                    <button className="icon-button" title="Следующий трек"><NextIcon width={22} height={22}/></button>
                    <button className="icon-button" title="Повтор"><RepeatIcon/></button>
                </div>

                <div className="progress-row">
                    <span>{formatTime(currentTime)}</span>
                    <span className="progress">
                        <span className="progress-fill" style={{width: progress + "%"}}/>
                        <span className="progress-thumb" style={{left: progress + "%"}}/>
                    </span>
                    <span>{formatTime(track.duration)}</span>
                </div>
            </div>

            <div className="player-right">
                <button className="icon-button" title="Редактор"><EditorIcon/></button>
                <button className="icon-button" title="Очередь"><QueueIcon/></button>
                <button className="icon-button" title="Громкость"><VolumeIcon/></button>
                <span className="volume"/>
            </div>
        </footer>
    )
}

export default Player
