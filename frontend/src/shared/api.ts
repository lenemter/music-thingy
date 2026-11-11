import type { Service, User } from "./types.ts";
import type { MusicSearchResponse, PlaybackInfo, PlaylistRead, ServiceConnection, ServiceItem, TrackRead, DeviceCode } from "./music/types.ts";

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
    { text: "CLIENT_ID and CLIENT_SECRET", message: "Вход через YouTube ещё не настроен на сервере" },
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

export async function fetchServices(): Promise<Service[]> {
    const [items, connections]: [ServiceItem[], ServiceConnection[]] = await Promise.all([
        requestJson("/api/services"),
        requestJson("/api/services/connections"),
    ]);

    return connections.map((connection) => {
        const item = items.find((entry) => entry.service === connection.service);
        return {
            id: connection.service,
            code: connection.code,
            name: connection.name,
            shortName: item?.shortName ?? connection.name,
            online: connection.connected && connection.is_active,
            linked: connection.connected,
            accountName: connection.account_name ?? undefined,
        };
    });
}

export async function setServiceActive(service: string, isActive: boolean): Promise<Service[]> {
    await requestJson(`/api/services/${service}/toggle`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: isActive }),
    });
    return fetchServices();
}

export type VkLoginResult = {
    status: "connected" | "need_code" | "need_captcha"
    validation_type?: string
    phone_mask?: string
    invalid_code?: boolean
}

export async function loginVk(login: string, password: string, code?: string): Promise<VkLoginResult> {
    return postJson("/api/services/vk/login", { login, password, code });
}

export async function disconnectService(service: string): Promise<void> {
    await requestJson(`/api/services/${service}/disconnect`, { method: "DELETE" });
}

export async function startDeviceLink(service: string): Promise<DeviceCode> {
    return requestJson(`/api/services/${service}/oauth/device-code`, { method: "POST" });
}

export async function pollDeviceLink(service: string, deviceCode: string): Promise<{ status: string }> {
    return postJson(`/api/services/${service}/oauth/poll-token`, { device_code: deviceCode });
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

export async function fetchMyPlaylists(): Promise<PlaylistRead[]> {
    return requestJson("/api/music/me/playlists");
}

export async function fetchServicePlaylist(service: string, serviceId: string): Promise<PlaylistRead> {
    return requestJson(`/api/music/playlists/${service}/${encodeURIComponent(serviceId)}`);
}

export async function fetchFavorites(): Promise<TrackRead[]> {
    return requestJson("/api/music/me/favorites?limit=100");
}
