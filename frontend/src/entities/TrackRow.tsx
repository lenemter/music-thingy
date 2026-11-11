import { useState } from "react";
import Cover from "./Cover.tsx";
import { formatTime } from "../shared/format.ts";
import type { Service, Track } from "../shared/types.ts";
import { getServiceName } from "../shared/music/services.ts";
import { setTrackLiked } from "../shared/favorites.ts";
import EditorIcon from "../shared/icons/editor.svg?react";
import HeartIcon from "../shared/icons/heart.svg?react";
import HeartFilledIcon from "../shared/icons/heart-filled.svg?react";
import Equalizer from "./Equalizer.tsx";

type TrackRowProps = {
    track: Track
    number: number
    isPlaying: boolean
    services: Service[]
    onPlay: (track: Track) => void
}

function TrackRow({ track, number, isPlaying, services, onPlay }: TrackRowProps) {
    const [isLiked, setIsLiked] = useState(track.liked === true);

    function getTagTitle(code: string) {
        const service = services.find((item) => item.code === code);
        return service ? service.name : getServiceName(code);
    }

    return (
        <li className={isPlaying ? "track playing" : "track"} onClick={() => onPlay(track)}>
            {isPlaying ? (
                <Equalizer/>
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
                        title={getTagTitle(source)}
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
                    const newValue = !isLiked;
                    setIsLiked(newValue);
                    setTrackLiked(track, newValue).catch(() => setIsLiked(!newValue));
                }}
            >
                {isLiked ? <HeartFilledIcon/> : <HeartIcon/>}
            </button>
        </li>
    )
}

export default TrackRow
