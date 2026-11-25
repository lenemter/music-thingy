import { useLayoutEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";

type MarqueeTextProps = {
    text: string
    className?: string
}

const SPEED = 40;
const PAUSE_SHARE = 0.4;
const FADE = 16;

function MarqueeText({ text, className }: MarqueeTextProps) {
    const boxRef = useRef<HTMLSpanElement>(null);
    const textRef = useRef<HTMLSpanElement>(null);
    const [shift, setShift] = useState(0);

    useLayoutEffect(() => {
        const box = boxRef.current;
        const inner = textRef.current;
        if (!box || !inner) {
            return;
        }
        function measure() {
            if (!box || !inner) {
                return;
            }
            const overflow = inner.scrollWidth - box.clientWidth;
            setShift(overflow > 2 ? Math.ceil(overflow) + FADE : 0);
        }
        measure();
        const observer = new ResizeObserver(measure);
        observer.observe(box);
        let isActive = true;
        document.fonts?.ready.then(() => isActive && measure());
        return () => {
            isActive = false;
            observer.disconnect();
        };
    }, [text]);

    const moveSeconds = (shift / SPEED) * 2;
    const style = shift > 0
        ? { "--marquee-shift": -shift + "px", "--marquee-duration": Math.max(6, moveSeconds / (1 - PAUSE_SHARE)).toFixed(1) + "s" } as CSSProperties
        : undefined;

    return (
        <span ref={boxRef} className={["marquee", shift > 0 ? "is-moving" : "", className ?? ""].filter(Boolean).join(" ")} style={style} title={shift > 0 ? text : undefined}>
            <span ref={textRef} className="marquee-text">{text}</span>
        </span>
    )
}

export default MarqueeText
