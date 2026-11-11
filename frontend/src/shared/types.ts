import type { ServiceId } from "./music/types.ts";

export type Service = {
    id: ServiceId
    code: string
    name: string
    shortName: string
    online: boolean
    linked: boolean
    accountName?: string
}

export type Track = {
    id: string
    title: string
    artist: string
    cover: string
    duration: number
    sources: string[]
    source: string
    edited?: boolean
    liked?: boolean
    service?: ServiceId
    serviceId?: string
    audioUrl?: string
    externalUrl?: string
    // Название сервиса, если он отключён и трек сейчас нельзя включить
    unavailable?: string
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
    audioUrl: string
    isEdited: boolean
    artist: string
    cover?: string
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
    email: string
}
