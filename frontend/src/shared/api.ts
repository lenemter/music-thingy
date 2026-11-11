import type { Album, Playlist, Service, Track, User, UserFile, Wave } from "./types.ts";
import type { LinkStartResponse, LinkStatusResponse, MusicSearchResponse, PlaybackInfo, ServiceItem, TrackRead, UserFileRead } from "./music/types.ts";

const TOKENS_KEY = "signal-tokens";
const USER_KEY = "signal-user";

type Tokens = {
    access: string
    refresh: string
}

const translations = [
    { text: "No active account found", message: "Неверная почта или пароль" },
    { text: "already exists", message: "Пользователь с такой почтой уже зарегистрирован" },
    { text: "valid email", message: "Введите корректную почту" },
    { text: "at least 8 characters", message: "Пароль должен быть не короче 8 символов" },
    { text: "Token has expired", message: "Сессия истекла, войдите снова" },
    { text: "Could not validate token", message: "Сессия истекла, войдите снова" },
    { text: "Not authenticated", message: "Нужно войти в аккаунт" },
    { text: "Unsupported audio format", message: "Такой формат не поддерживается — нужен MP3, WAV, FLAC, OGG, M4A или AAC" },
    { text: "exceeds maximum size", message: "Файл больше 50 МБ" },
];

function translate(message: string) {
    for (const item of translations) {
        if (message.includes(item.text)) {
            return item.message;
        }
    }
    return message;
}

export class ApiError extends Error {
    status: number

    constructor(message: string, status: number) {
        super(message);
        this.status = status;
    }
}

function getErrorMessage(data: Record<string, unknown>) {
    const detail = data.detail;

    if (typeof detail === "string") {
        return translate(detail);
    }

    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0] as Record<string, unknown>;
        return translate(String(first.msg ?? first));
    }

    for (const key in data) {
        const value = data[key];
        if (Array.isArray(value) && value.length > 0) {
            return translate(String(value[0]));
        }
    }

    return "Что-то пошло не так, попробуйте ещё раз";
}

function saveTokens(tokens: Tokens) {
    localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
}

function loadTokens(): Tokens | null {
    const text = localStorage.getItem(TOKENS_KEY);
    if (text === null) {
        return null;
    }
    return JSON.parse(text);
}

function saveUser(user: User) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function loadUser(): User | null {
    const text = localStorage.getItem(USER_KEY);
    if (text === null || loadTokens() === null) {
        return null;
    }
    return JSON.parse(text);
}

export function getAccessToken() {
    const tokens = loadTokens();
    return tokens ? tokens.access : null;
}

async function sendRequest(url: string, options: RequestInit) {
    const token = getAccessToken();
    const headers: Record<string, string> = {
        Accept: "application/json",
        ...(options.headers as Record<string, string> || {}),
    };

    if (token && !headers["Authorization"]) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    let response: Response;
    try {
        response = await fetch(url, { ...options, headers });
    } catch {
        throw new ApiError("Сервер недоступен, попробуйте позже", 0);
    }

    if (response.status === 204) {
        return null;
    }

    let data: any = {};
    try {
        data = await response.json();
    } catch {
        data = {};
    }

    if (!response.ok) {
        throw new ApiError(getErrorMessage(data), response.status);
    }

    return data;
}

async function requestJson(url: string, options: RequestInit = {}) {
    try {
        return await sendRequest(url, options);
    } catch (error) {
        const isAuthUrl = url.startsWith("/api/auth/token") || url.startsWith("/api/auth/login");
        if (error instanceof ApiError && error.status === 401 && !isAuthUrl && await refreshTokens()) {
            return sendRequest(url, options);
        }
        throw error;
    }
}

async function postJson(url: string, body: object) {
    return requestJson(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

// ================= AUTH =================

export async function fetchMe(): Promise<User | null> {
    try {
        const data = await requestJson("/api/auth/me");
        const email = String(data.email);
        const name = data.display_name ? String(data.display_name) : email.split("@")[0];
        const user: User = { name, email };
        saveUser(user);
        return user;
    } catch {
        return null;
    }
}

export async function login(email: string, password: string, name?: string) {
    const data = await postJson("/api/auth/token/", { email, password });
    saveTokens({ access: String(data.access), refresh: String(data.refresh) });
    const user: User = { name: name || email.split("@")[0], email };
    saveUser(user);

    const me = await fetchMe();
    return me ?? user;
}

export async function register(email: string, name: string, password: string) {
    await postJson("/api/auth/register/", { email, display_name: name, password });
    return login(email, password, name);
}

let currentRefresh: Promise<boolean> | null = null;

async function requestNewTokens() {
    const tokens = loadTokens();
    if (tokens === null) {
        return false;
    }

    try {
        const data = await sendRequest("/api/auth/token/refresh/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh: tokens.refresh }),
        });
        saveTokens({ access: String(data.access), refresh: String(data.refresh ?? tokens.refresh) });
        return true;
    } catch (error) {
        if (error instanceof ApiError && (error.status === 400 || error.status === 401 || error.status === 422)) {
            return false;
        }
        return true;
    }
}

export function refreshTokens() {
    if (currentRefresh === null) {
        currentRefresh = requestNewTokens().finally(() => {
            currentRefresh = null;
        });
    }
    return currentRefresh;
}

export function logout() {
    localStorage.removeItem(TOKENS_KEY);
    localStorage.removeItem(USER_KEY);
}

// ================= SERVICES =================

function serviceFromItem(item: ServiceItem): Service {
    return {
        id: item.service,
        code: item.code,
        name: item.name,
        shortName: item.shortName,
        online: item.online,
        linked: item.linked ?? false,
    };
}

export async function fetchServices(): Promise<Service[]> {
    const items: ServiceItem[] = await requestJson("/api/services");
    return items.map(serviceFromItem);
}

export async function updateServicePreferences(enabledServices: string[]): Promise<Service[]> {
    const items: ServiceItem[] = await requestJson("/api/services/preferences", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled_services: enabledServices }),
    });
    return items.map(serviceFromItem);
}

export async function startServiceLink(service: string): Promise<LinkStartResponse> {
    return requestJson(`/api/services/${service}/link`, { method: "POST" });
}

export async function getServiceLinkStatus(service: string, sessionId: string): Promise<LinkStatusResponse> {
    return requestJson(`/api/services/${service}/link/${sessionId}`);
}

export async function unlinkService(service: string): Promise<void> {
    await requestJson(`/api/services/${service}/link`, { method: "DELETE" });
}

// ================= MUSIC & SEARCH =================

export type SearchMusicParams = {
    query: string
    services?: string[]
    types?: string[]
    limit?: number
}

export async function searchMusic({ query, services, types, limit = 10 }: SearchMusicParams): Promise<MusicSearchResponse> {
    const params = new URLSearchParams();
    params.set("q", query);
    if (services && services.length > 0) params.set("services", services.join(","));
    if (types && types.length > 0) params.set("types", types.join(","));
    if (limit) params.set("limit", String(limit));

    return requestJson(`/api/music/search?${params.toString()}`);
}

export async function fetchTrack(service: string, serviceId: string): Promise<TrackRead> {
    return requestJson(`/api/music/tracks/${service}/${encodeURIComponent(serviceId)}`);
}

export async function fetchPlayback(service: string, serviceId: string): Promise<PlaybackInfo> {
    return requestJson(`/api/music/playback/${service}/${encodeURIComponent(serviceId)}`);
}

// ================= PLAYLISTS =================

export async function fetchPlaylists(): Promise<Playlist[]> {
    return requestJson("/api/playlists");
}

export async function createPlaylist(name: string, description?: string, coverUrl?: string): Promise<Playlist> {
    return requestJson("/api/playlists", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description, cover_url: coverUrl }),
    });
}

export async function fetchPlaylistDetails(playlistId: number): Promise<Playlist & { tracks: any[] }> {
    return requestJson(`/api/playlists/${playlistId}`);
}

export async function addTrackToPlaylist(playlistId: number, track: Partial<Track> & { service: string; service_id: string }): Promise<any> {
    return requestJson(`/api/playlists/${playlistId}/tracks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            service: track.service,
            service_id: track.service_id,
            title: track.title,
            artist: track.artist,
            cover_url: track.cover,
            duration: track.duration,
        }),
    });
}

export async function removeTrackFromPlaylist(playlistId: number, trackId: number): Promise<void> {
    await requestJson(`/api/playlists/${playlistId}/tracks/${trackId}`, { method: "DELETE" });
}

export async function reorderPlaylist(playlistId: number, trackIds: number[]): Promise<any> {
    return requestJson(`/api/playlists/${playlistId}/reorder`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ track_ids: trackIds }),
    });
}

export async function deletePlaylist(playlistId: number): Promise<void> {
    await requestJson(`/api/playlists/${playlistId}`, { method: "DELETE" });
}

// ================= FAVORITES =================

export async function fetchFavoriteTracks(): Promise<Track[]> {
    return requestJson("/api/favorites/tracks");
}

export async function addFavoriteTrack(track: Track & { service?: string; service_id?: string }): Promise<Track> {
    return requestJson("/api/favorites/tracks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            service: track.service || track.source,
            service_id: track.service_id || String(track.id),
            title: track.title,
            artist: track.artist,
            cover_url: track.cover,
            duration: track.duration,
            sources: track.sources,
            is_edited: track.edited || false,
        }),
    });
}

export async function removeFavoriteTrack(service: string, serviceId: string): Promise<void> {
    await requestJson(`/api/favorites/tracks/${service}/${serviceId}`, { method: "DELETE" });
}

export async function fetchFavoriteAlbums(): Promise<Album[]> {
    return requestJson("/api/favorites/albums");
}

// ================= HISTORY & RECOMMENDATIONS =================

export async function recordListeningHistory(track: Track & { service?: string; service_id?: string }): Promise<void> {
    await requestJson("/api/history", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            service: track.service || track.source,
            service_id: track.service_id || String(track.id),
            title: track.title,
            artist: track.artist,
            cover_url: track.cover,
            duration: track.duration,
        }),
    });
}

export async function fetchContinueListening(limit = 6): Promise<Album[]> {
    return requestJson(`/api/history/albums?limit=${limit}`);
}

export async function fetchRecommendations(limit = 10): Promise<Track[]> {
    return requestJson(`/api/recommendations?limit=${limit}`);
}

export async function fetchWave(): Promise<Wave> {
    return requestJson("/api/wave");
}

// ================= OWN MUSIC & UPLOADS =================

function fileFromRead(item: UserFileRead): UserFile {
    return {
        id: item.id,
        name: item.name,
        type: item.type,
        duration: item.duration,
        size: item.size,
        audioUrl: item.audio_url,
        isEdited: item.is_edited,
        artist: item.artist || "Моя музыка",
        cover: item.cover_url || undefined,
    };
}

export async function updateUpload(uploadId: number, data: { title: string, artist: string }): Promise<UserFile> {
    const item: UserFileRead = await requestJson(`/api/uploads/${uploadId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    return fileFromRead(item);
}

export async function uploadCover(uploadId: number, image: Blob): Promise<UserFile> {
    const formData = new FormData();
    formData.append("file", image, "cover.jpg");
    const item: UserFileRead = await requestJson(`/api/uploads/${uploadId}/cover`, {
        method: "PUT",
        body: formData,
    });
    return fileFromRead(item);
}

export async function removeCover(uploadId: number): Promise<void> {
    await requestJson(`/api/uploads/${uploadId}/cover`, { method: "DELETE" });
}

export async function fetchUploads(): Promise<UserFile[]> {
    const items: UserFileRead[] = await requestJson("/api/uploads");
    return items.map(fileFromRead);
}

export async function uploadAudioFile(file: File, title?: string, artist?: string): Promise<UserFile> {
    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);
    if (artist) formData.append("artist", artist);

    const item: UserFileRead = await requestJson("/api/uploads", {
        method: "POST",
        body: formData,
    });
    return fileFromRead(item);
}

export async function deleteUpload(uploadId: number): Promise<void> {
    await requestJson(`/api/uploads/${uploadId}`, { method: "DELETE" });
}

export function getUploadStreamUrl(uploadId: number): string {
    return `/api/uploads/${uploadId}/stream`;
}

// ================= AUDIO EDITOR =================

export type AudioEffectsOptions = {
    fade_in_sec?: number
    fade_out_sec?: number
    volume_gain_db?: number
    bass_boost_db?: number
    speed_factor?: number
    normalize?: boolean
    reverse?: boolean
    echo_delay_sec?: number
    echo_decay?: number
    save_as_new?: boolean
    new_name?: string
}

export async function trimAudio(uploadId: number, startSec: number, endSec?: number, newName?: string): Promise<UserFile> {
    return requestJson("/api/editor/trim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            upload_id: uploadId,
            start_sec: startSec,
            end_sec: endSec,
            save_as_new: true,
            new_name: newName,
        }),
    });
}

export async function applyAudioEffects(uploadId: number, options: AudioEffectsOptions): Promise<UserFile> {
    return requestJson("/api/editor/effects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            upload_id: uploadId,
            ...options,
        }),
    });
}

export async function processAudioPipeline(uploadId: number, config: AudioEffectsOptions & { start_sec?: number; end_sec?: number; output_format?: string }): Promise<UserFile> {
    return requestJson("/api/editor/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            upload_id: uploadId,
            ...config,
        }),
    });
}
