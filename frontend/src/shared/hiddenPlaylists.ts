import { loadUser } from "./api.ts";

const listeners = new Set<() => void>();

function storageKey() {
    return "signal-hidden-playlists:" + (loadUser()?.email ?? "guest");
}

export function getHiddenPlaylists(): string[] {
    try {
        const value = JSON.parse(localStorage.getItem(storageKey()) ?? "[]");
        return Array.isArray(value) ? value : [];
    } catch {
        return [];
    }
}

export function setPlaylistHidden(id: string, isHidden: boolean) {
    const list = getHiddenPlaylists().filter((item) => item !== id);
    if (isHidden) {
        list.push(id);
    }
    try {
        localStorage.setItem(storageKey(), JSON.stringify(list));
    } catch {
        return;
    }
    listeners.forEach((listener) => listener());
}

export function subscribeHiddenPlaylists(listener: () => void) {
    listeners.add(listener);
    return () => {
        listeners.delete(listener);
    };
}
