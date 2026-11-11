export type EngineEvents = {
    onTime: (currentTime: number, duration: number) => void
    onPlayingChange: (isPlaying: boolean) => void
    onEnded: () => void
    onError: (message: string) => void
}

export type PlayerEngine = {
    load: (src: string) => Promise<void>
    play: () => void
    pause: () => void
    seek: (seconds: number) => void
    setVolume: (volume: number) => void
    destroy: () => void
}

export type PlaybackSource =
    | { kind: "audio" | "youtube" | "soundcloud", src: string }
    | { kind: "unsupported", message: string, externalUrl?: string }
