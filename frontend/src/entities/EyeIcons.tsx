type IconProps = {
    size?: number
}

export function EyeOffIcon({ size = 16 }: IconProps) {
    return (
        <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M3 3l18 18M10.6 6.2A9.7 9.7 0 0 1 12 6c6 0 9.5 6 9.5 6a17 17 0 0 1-3 3.6M6.5 7.6A16.5 16.5 0 0 0 2.5 12S6 18 12 18a9.3 9.3 0 0 0 3.8-.8M9.9 9.9a3 3 0 0 0 4.2 4.2"/>
        </svg>
    )
}

export function EyeIcon({ size = 16 }: IconProps) {
    return (
        <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M2.5 12S6 6 12 6s9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6z"/>
            <circle cx="12" cy="12" r="3"/>
        </svg>
    )
}
