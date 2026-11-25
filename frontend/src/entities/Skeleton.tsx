import type { CSSProperties } from "react";

type SkeletonProps = {
    width?: number | string
    height?: number | string
    radius?: number | string
    className?: string
    style?: CSSProperties
}

export function Skeleton({ width, height, radius, className, style }: SkeletonProps) {
    return (
        <span
            className={className ? "sk " + className : "sk"}
            style={{ width, height, borderRadius: radius, ...style }}
            aria-hidden="true"
        />
    )
}

export function NoteIcon({ size = 44, strokeWidth = 1.5 }: { size?: number, strokeWidth?: number }) {
    return (
        <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M9 18V6l10-2v12"/>
            <circle cx="6" cy="18" r="3"/>
            <circle cx="16" cy="16" r="3"/>
        </svg>
    )
}

export function NoteOffIcon({ size = 44, strokeWidth = 1.5 }: { size?: number, strokeWidth?: number }) {
    return (
        <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M9 18V6l10-2v12M3 3l18 18"/>
            <circle cx="6" cy="18" r="3"/>
        </svg>
    )
}

const ROW_WIDTHS = [
    ["46%", "28%", 56],
    ["62%", "22%", 28],
    ["38%", "31%", 56],
    ["54%", "19%", 28],
    ["44%", "26%", 56],
    ["58%", "24%", 28],
] as const;

export function TrackRowSkeleton({ index = 0 }: { index?: number }) {
    const [title, artist, tags] = ROW_WIDTHS[index % ROW_WIDTHS.length];
    return (
        <li className="track track-skeleton" aria-hidden="true">
            <Skeleton width={20} height={12}/>
            <Skeleton className="sk-row-cover"/>
            <span className="track-info">
                <Skeleton width={title} height={14}/>
                <Skeleton width={artist} height={11}/>
            </span>
            <Skeleton width={tags} height={20} radius={6}/>
            <Skeleton width={34} height={12}/>
        </li>
    )
}

export function TrackListSkeleton({ count = 6, label = "Загружаем треки" }: { count?: number, label?: string }) {
    return (
        <ol className="track-list" aria-busy="true" aria-label={label}>
            {Array.from({ length: count }, (_, index) => <TrackRowSkeleton key={index} index={index}/>)}
        </ol>
    )
}

const CARD_WIDTHS = [["75%", "52%"], ["60%", "44%"], ["82%", "48%"]] as const;

export function PlaylistCardSkeleton({ index = 0 }: { index?: number }) {
    const [title, subtitle] = CARD_WIDTHS[index % CARD_WIDTHS.length];
    return (
        <div className="playlist-card playlist-card-skeleton" aria-hidden="true">
            <Skeleton className="playlist-cover card"/>
            <Skeleton width={title} height={16}/>
            <Skeleton width={subtitle} height={12}/>
        </div>
    )
}
