// Своё окно подтверждения вместо window.confirm: confirmAction(...) возвращает Promise<boolean>.
export type ConfirmIcon = "delete" | "logout" | "reset" | "disconnect"

export type ConfirmDetail = {
    label: string
    value: string
    accent?: boolean
}

export type ConfirmOptions = {
    title: string
    text: string
    confirmText: string
    danger?: boolean
    icon?: ConfirmIcon
    details?: ConfirmDetail[]
    // Если задан — показывается «Больше не спрашивать», выбор запоминается в браузере по этому ключу.
    rememberKey?: string
}

export type ConfirmRequest = ConfirmOptions & {
    id: number
    resolve: (value: boolean) => void
}

const REMEMBER_PREFIX = "signal-skip-confirm:";

const listeners = new Set<(request: ConfirmRequest) => void>();
let lastId = 0;

export function subscribeConfirm(listener: (request: ConfirmRequest) => void) {
    listeners.add(listener);
    return () => {
        listeners.delete(listener);
    };
}

function isSkipped(key: string) {
    try {
        return localStorage.getItem(REMEMBER_PREFIX + key) === "1";
    } catch {
        return false;
    }
}

export function rememberSkip(key: string) {
    try {
        localStorage.setItem(REMEMBER_PREFIX + key, "1");
    } catch {
        return;
    }
}

export function confirmAction(options: ConfirmOptions): Promise<boolean> {
    if (options.rememberKey && isSkipped(options.rememberKey)) {
        return Promise.resolve(true);
    }
    if (listeners.size === 0) {
        return Promise.resolve(window.confirm(options.title + "\n\n" + options.text));
    }
    return new Promise((resolve) => {
        lastId += 1;
        const request = { ...options, id: lastId, resolve };
        listeners.forEach((listener) => listener(request));
    });
}
