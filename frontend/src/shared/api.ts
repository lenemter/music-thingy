import type { Album, Playlist, Service, Track, User, UserFile, Wave } from "./types.ts";

const TOKENS_KEY = "signal-tokens";
const USER_KEY = "signal-user";

type Tokens = {
    access: string
    refresh: string
}

const translations: Record<string, string> = {
    "No active account found with the given credentials": "Неверная почта или пароль",
    "user with this email address already exists.": "Пользователь с такой почтой уже зарегистрирован",
    "Enter a valid email address.": "Введите корректную почту",
    "Ensure this field has at least 8 characters.": "Пароль должен быть не короче 8 символов",
    "This field may not be blank.": "Заполните все поля",
    "This field is required.": "Заполните все поля",
    "Token is invalid": "Сессия истекла, войдите снова",
};

function translate(message: string) {
    return translations[message] ?? message;
}

function getErrorMessage(data: Record<string, unknown>) {
    if (typeof data.detail === "string") {
        return translate(data.detail);
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

async function requestJson(url: string, options: RequestInit = {}) {
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
        throw new Error("Сервер недоступен, попробуйте позже");
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
        throw new Error(getErrorMessage(data));
    }

    return data;
}

async function postJson(url: string, body: object) {
    return requestJson(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

// ================= AUTH =================

export async function login(email: string, password: string, name?: string) {
    const data = await postJson("/api/auth/token/", { email, password });
    saveTokens({ access: String(data.access), refresh: String(data.refresh) });
    const user: User = { name: name || email.split("@")[0], email };
    saveUser(user);
    return user;
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
        const data = await postJson("/api/auth/token/refresh/", { refresh: tokens.refresh });
        saveTokens({ access: String(data.access), refresh: String(data.refresh ?? tokens.refresh) });
        return true;
    } catch {
        return false;
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

export async function fetchServices(): Promise<Service[]> {
    return requestJson("/api/services");
}

export async function updateServicePreferences(enabledServices: string[]): Promise<Service[]> {
    return requestJson("/api/services/preferences", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled_services: enabledServices }),
    });
}

// ================= MUSIC & SEARCH =================

export type SearchMusicParams = {
    query: string
    services?: string[]
    types?: string[]
    limit?: number
}

export type SearchMusicResult = {
    query: string
    tracks: Track[]
    albums: Album[]
    artists: Array<{ service: string; service_id: string; name: string; cover?: string }>
    playlists: Array<{ id: number; name: string; cover: string; description?: string }>
    errors: Array<{ service: string; kind: string; message: string }>
}

export async function searchMusic({ query, services, types, limit = 10 }: SearchMusicParams): Promise<SearchMusicResult> {
    const params = new URLSearchParams();
    params.set("q", query);
    if (services && services.length > 0) params.set("services", services.join(","));
    if (types && types.length > 0) params.set("types", types.join(","));
    if (limit) params.set("limit", String(limit));

    return requestJson(`/api/music/search?${params.toString()}`);
}

export async function fetchTrack(service: string, serviceId: string): Promise<Track> {
    return requestJson(`/api/music/tracks/${service}/${serviceId}`);
}

export async function fetchPlayback(service: string, serviceId: string): Promise<{ kind: string; ref: string }> {
    return requestJson(`/api/music/playback/${service}/${serviceId}`);
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

export async function fetchUploads(): Promise<UserFile[]> {
    return requestJson("/api/uploads");
}

export async function uploadAudioFile(file: File, title?: string, artist?: string): Promise<UserFile> {
    const token = getAccessToken();
    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);
    if (artist) formData.append("artist", artist);

    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const resp = await fetch("/api/uploads", {
        method: "POST",
        headers,
        body: formData,
    });

    if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(getErrorMessage(data));
    }

    return resp.json();
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
