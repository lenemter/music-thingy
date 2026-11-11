// Короткие всплывающие сообщения внизу экрана: showToast("...")
export type ToastMessage = {
    id: number
    text: string
}

const listeners = new Set<(toast: ToastMessage) => void>();
let lastId = 0;

export function showToast(text: string) {
    lastId += 1;
    const toast = { id: lastId, text };
    listeners.forEach((listener) => listener(toast));
}

export function subscribeToast(listener: (toast: ToastMessage) => void) {
    listeners.add(listener);
    return () => {
        listeners.delete(listener);
    };
}
