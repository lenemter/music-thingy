export type ServiceId = "yandex" | "spotify" | "soundcloud" | "youtube" | "vk" | "local"

export type SearchType = "track" | "album" | "artist" | "playlist"

export type PlaybackInfo = {
    kind: string
    ref: string
    direct_audio_url?: string | null
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
    stream_url?: string | null
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

export type PlaylistRead = {
    id: number
    service: ServiceId
    service_id: string
    name: string
    cover: string
    artwork_url: string | null
    description: string | null
    owner_name: string | null
    tracks_count: number | null
    external_url: string | null
    tracks: TrackRead[] | null
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
}

export type ServiceConnection = {
    service: ServiceId
    code: string
    name: string
    connected: boolean
    is_active: boolean
    account_name: string | null
    account_id: string | null
}

export type DeviceCode = {
    device_code: string
    user_code: string
    verification_url: string
    expires_in: number
    interval: number
}
