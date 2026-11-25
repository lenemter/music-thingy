import { useState } from "react";
import Grain from "./Grain.tsx";
import { NoteIcon, NoteOffIcon } from "./Skeleton.tsx";
import { hiResCover } from "../shared/coverTemplates.ts";

type CoverProps = {
    src: string
    size: "small" | "row" | "card" | "now-playing"
    fallback?: string
    onAccent?: boolean
}

const ICON_SIZE = { small: 12, row: 18, card: 44, "now-playing": 22 };

function Cover({ src, size, fallback, onAccent = false }: CoverProps) {
    const [loaded, setLoaded] = useState<string | null>(null);
    const [failed, setFailed] = useState<string[]>([]);

    const candidates = [hiResCover(src), fallback].filter((item): item is string => Boolean(item));
    const current = candidates.find((item) => !failed.includes(item));
    const isLoaded = current !== undefined && loaded === current;
    const iconSize = ICON_SIZE[size];

    const classes = ["cover", size];
    if (!current) {
        classes.push("cover-broken");
    } else if (!isLoaded) {
        classes.push("sk", "cover-loading");
        if (onAccent) {
            classes.push("on-accent");
        }
    }

    return (
        <span className={classes.join(" ")}>
            {current ? (
                <>
                    {!isLoaded && size !== "small" && <span className="cover-icon"><NoteIcon size={iconSize}/></span>}
                    <img
                        key={current}
                        src={current}
                        alt=""
                        className={isLoaded ? "" : "hidden"}
                        ref={(img) => {
                            if (img && img.complete && img.naturalWidth > 0 && loaded !== current) {
                                setLoaded(current);
                            }
                        }}
                        onLoad={() => setLoaded(current)}
                        onError={() => setFailed((list) => [...list, current])}
                    />
                </>
            ) : (
                <span className="cover-icon"><NoteOffIcon size={iconSize} strokeWidth={size === "card" ? 1.5 : 1.8}/></span>
            )}
            {isLoaded && !onAccent && <Grain/>}
        </span>
    )
}

export default Cover
