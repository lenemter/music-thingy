export type Service = {
    code: string
    name: string
    shortName: string
    online: boolean
}

export type Track = {
    id: number
    title: string
    artist: string
    cover: string
    duration: number
    sources: string[]
    source: string
    edited?: boolean
    liked?: boolean
}

export type Album = {
    id: number
    title: string
    subtitle: string
    cover: string
}

export type Playlist = {
    id: number
    name: string
    cover: string
}

export type UserFile = {
    id: number
    name: string
    type: string
    duration: number
    size: number
}

export type Wave = {
    date: string
    title: string
    description: string
    trackCount: number
    duration: number
}

export type User = {
    name: string
}
