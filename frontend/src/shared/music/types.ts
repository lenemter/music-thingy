export type ServiceId = "yandex" | "spotify" | "soundcloud" | "youtube" | "local"

export type SearchType = "track" | "album" | "artist" | "playlist"

export type PlaybackInfo = {
    kind: string
    ref: string
}

export type TrackRead = {
    id: number
    track_key: string | null
    service: ServiceId
    service_id: string
    title: string
    artist: string
    cover: string
    duration: number
    sources: string[]
    source: string
    edited: boolean
    liked: boolean
    playback: PlaybackInfo | null
    direct_audio_url: string | null
    external_url: string | null
}

export type AlbumRead = {
    id: number
    service: ServiceId
    service_id: string
    title: string
    subtitle: string
    cover: string
}

export type ArtistRead = {
    service: ServiceId
    service_id: string
    name: string
    genres: string[]
    cover: string | null
    external_url: string | null
}

export type PlaylistSearchResult = {
    id: number
    service: ServiceId
    service_id: string
    name: string
    cover: string
    description: string | null
    tracks_count: number
}

export type ServiceError = {
    service: ServiceId
    kind: string
    message: string
    status_code: number | null
}

export type MusicSearchResponse = {
    query: string
    tracks: TrackRead[]
    albums: AlbumRead[]
    artists: ArtistRead[]
    playlists: PlaylistSearchResult[]
    errors: ServiceError[]
}

export type ServiceItem = {
    code: string
    name: string
    shortName: string
    service: ServiceId
    online: boolean
    linked?: boolean
}

export type LinkStartResponse = {
    session_id: string
    kind: "device_code" | "redirect"
    url: string
    user_code: string | null
    expires_in: number
    interval: number
}

export type LinkStatusResponse = {
    status: "pending" | "linked" | "expired" | "denied"
    detail: string | null
}

export type UserFileRead = {
    id: number
    name: string
    type: string
    duration: number
    size: number
    size_bytes: number
    audio_url: string
    artist?: string | null
    cover_url?: string | null
    is_edited: boolean
    parent_id: number | null
    edit_summary: string | null
    created_at: string
}
