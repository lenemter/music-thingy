const scripts: Record<string, Promise<void>> = {};

export const LOAD_TIMEOUT = 15000;

export function withTimeout<T>(promise: Promise<T>, message: string): Promise<T> {
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error(message)), LOAD_TIMEOUT);
        promise.then(
            (value) => {
                clearTimeout(timer);
                resolve(value);
            },
            (error) => {
                clearTimeout(timer);
                reject(error);
            },
        );
    });
}

export function loadScript(src: string) {
    if (!scripts[src]) {
        const loading = new Promise<void>((resolve, reject) => {
            const script = document.createElement("script");
            script.src = src;
            script.async = true;
            script.onload = () => resolve();
            script.onerror = () => {
                delete scripts[src];
                reject(new Error("Не удалось загрузить плеер сервиса"));
            };
            document.head.appendChild(script);
        });
        scripts[src] = withTimeout(loading, "Плеер сервиса не отвечает");
        scripts[src].catch(() => delete scripts[src]);
    }
    return scripts[src];
}

export function createHiddenBox() {
    let host = document.getElementById("player-hidden-host");
    if (host === null) {
        host = document.createElement("div");
        host.id = "player-hidden-host";
        document.body.appendChild(host);
    }

    const box = document.createElement("div");
    host.appendChild(box);
    return box;
}
