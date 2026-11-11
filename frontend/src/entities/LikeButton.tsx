import { useState } from "react";
import { setTrackLiked } from "../shared/favorites.ts";
import type { Track } from "../shared/types.ts";
import HeartIcon from "../shared/icons/heart.svg?react";
import HeartFilledIcon from "../shared/icons/heart-filled.svg?react";

function LikeButton({ track }: { track: Track }) {
    const [isLiked, setIsLiked] = useState(track.liked === true);

    return (
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
    )
}

export default LikeButton
