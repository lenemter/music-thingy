import { useState } from "react";
import Cover from "../entities/Cover.tsx";
import { formatTime } from "../shared/format.ts";
import type { Service, Track } from "../shared/types.ts";
import EditorIcon from "../shared/icons/editor.svg?react";
import HeartIcon from "../shared/icons/heart.svg?react";
import HeartFilledIcon from "../shared/icons/heart-filled.svg?react";
import equalizer from "../shared/images/equalizer.svg";

type TrackRowProps = {
    track: Track
    number: number
    isPlaying: boolean
    services: Service[]
    onPlay: (track: Track) => void
}

function TrackRow({ track, number, isPlaying, services, onPlay }: TrackRowProps) {
    const [isLiked, setIsLiked] = useState(track.liked === true);

    function getServiceName(code: string) {
        const service = services.find((item) => item.code === code);
        return service ? service.name : code;
    }

    return (
        <li className={isPlaying ? "track playing" : "track"} onClick={() => onPlay(track)}>
            {isPlaying ? (
                <img src={equalizer} alt="Сейчас играет" title="Сейчас играет"/>
            ) : (
                <span className="track-number">{number < 10 ? "0" + number : number}</span>
            )}

            <Cover src={track.cover} size="row"/>

            <span className="track-info">
                <span className="track-title">{track.title}</span>
                <span className="track-artist">
                    {track.artist}
                    {track.edited && <span style={{color: "var(--accent)"}} title="С вашими правками"><EditorIcon width={12} height={12}/></span>}
                </span>
            </span>

            <span className="tags">
                {track.sources.map((source) => (
                    <span
                        key={source}
                        className={isPlaying && source === track.source ? "tag active" : "tag"}
                        title={getServiceName(source)}
                    >
                        {source}
                    </span>
                ))}
            </span>

            <span className="mono track-time">{formatTime(track.duration)}</span>

            <button
                className={isLiked ? "icon-button liked" : "icon-button"}
                title={isLiked ? "Убрать из избранного" : "В избранное"}
                onClick={(event) => {
                    event.stopPropagation();
                    setIsLiked(!isLiked);
                }}
            >
                {isLiked ? <HeartFilledIcon/> : <HeartIcon/>}
            </button>
        </li>
    )
}

type RecommendationsProps = {
    tracks: Track[]
    currentTrack: Track
    services: Service[]
    onPlay: (track: Track) => void
}

function Recommendations({ tracks, currentTrack, services, onPlay }: RecommendationsProps) {
    return (
        <section className="section recommendations">
            <div className="section-header">
                <h2>Рекомендации для вас</h2>
                <span className="mono">по истории из всех сервисов</span>
            </div>

            <ol className="track-list">
                {tracks.map((track, index) => (
                    <TrackRow
                        key={track.id}
                        track={track}
                        number={index + 1}
                        isPlaying={track.id === currentTrack.id}
                        services={services}
                        onPlay={onPlay}
                    />
                ))}
            </ol>
        </section>
    )
}

export default Recommendations
