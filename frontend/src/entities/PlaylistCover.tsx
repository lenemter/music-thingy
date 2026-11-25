import { useState } from "react";
import Grain from "./Grain.tsx";
import { formatTime, trackCount } from "../shared/format.ts";
import type { LibraryPlaylist } from "../shared/usePlaylists.ts";
import HeartFilledIcon from "../shared/icons/heart-filled.svg?react";
import { EyeOffIcon } from "./EyeIcons.tsx";
import { NoteIcon } from "./Skeleton.tsx";
import { hiResCover } from "../shared/coverTemplates.ts";

type PlaylistCoverProps = {
    playlist: LibraryPlaylist
    size: "small" | "card"
}

function getStarPoints() {
    const points: string[] = [];
    for (let i = 0; i < 16; i++) {
        const angle = (Math.PI / 8) * i - Math.PI / 2;
        const radius = i % 2 === 0 ? (i % 4 === 0 ? 50 : 34) : 3.5;
        points.push((50 + radius * Math.cos(angle)).toFixed(2) + "," + (50 + radius * Math.sin(angle)).toFixed(2));
    }
    return points.join(" ");
}

const starPoints = getStarPoints();

function GeneratedCover({ playlist, size }: PlaylistCoverProps) {
    const meta = playlist.duration > 0
        ? trackCount(playlist.tracksCount).toUpperCase() + " · " + formatTime(playlist.duration)
        : trackCount(playlist.tracksCount).toUpperCase();

    return (
        <span className="playlist-generated">
            {size === "card" && <span className="playlist-generated-meta">{meta}</span>}
            {playlist.kind === "liked" ? (
                <HeartFilledIcon className="playlist-generated-mark heart"/>
            ) : (
                <svg className="playlist-generated-mark" viewBox="0 0 100 100" aria-hidden="true">
                    <polygon points={starPoints} fill="currentColor"/>
                </svg>
            )}
            {size === "card" && <span className="playlist-generated-name">{playlist.name}</span>}
        </span>
    )
}

function PlaylistCover({ playlist, size }: PlaylistCoverProps) {
    const [isLoaded, setIsLoaded] = useState(false);
    const [isBroken, setIsBroken] = useState(false);
    const classes = ["playlist-cover", size];
    if (playlist.unavailable) {
        classes.push("unavailable");
    }

    if (playlist.hidden && size === "card") {
        return (
            <span className="playlist-cover card playlist-hidden-cover">
                <EyeOffIcon size={40}/>
            </span>
        );
    }

    let content;
    if (playlist.cover && !isBroken) {
        if (!isLoaded) {
            classes.push("sk", "loading");
        }
        content = (
            <>
                {!isLoaded && <span className="playlist-loading"><NoteIcon size={size === "card" ? 44 : 14}/></span>}
                <img
                    src={hiResCover(playlist.cover)}
                    alt=""
                    className={isLoaded ? "" : "hidden"}
                    onLoad={() => setIsLoaded(true)}
                    onError={() => setIsBroken(true)}
                />
            </>
        );
    } else if (playlist.covers.length > 0) {
        const tiles = playlist.covers.slice(0, 4);
        content = (
            <span className={"playlist-collage tiles-" + tiles.length}>
                {tiles.map((cover) => <img key={cover} src={hiResCover(cover)} alt=""/>)}
            </span>
        );
    } else {
        content = <GeneratedCover playlist={playlist} size={size}/>;
    }

    return (
        <span className={classes.join(" ")}>
            {content}
            <Grain/>
            {playlist.unavailable && size === "card" && (
                <span className="playlist-unavailable">
                    НЕДОСТУПНО<br/>ПОДКЛЮЧИТЕ {playlist.unavailable.toUpperCase()}
                </span>
            )}
        </span>
    )
}

export default PlaylistCover
