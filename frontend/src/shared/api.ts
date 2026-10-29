import type { User } from "./types.ts";

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

async function postJson(url: string, body: object) {
    let response: Response;

    try {
        response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
    } catch {
        throw new Error("Сервер недоступен, попробуйте позже");
    }

    let data: Record<string, unknown> = {};
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
