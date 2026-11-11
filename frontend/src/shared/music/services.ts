import type { Service } from "../types.ts";

export const defaultServices: Service[] = [
    { id: "yandex", code: "ЯМ", name: "Яндекс Музыка", shortName: "Яндекс", online: false, linked: false },
    { id: "spotify", code: "SP", name: "Spotify", shortName: "Spotify", online: false, linked: false },
    { id: "soundcloud", code: "SC", name: "SoundCloud", shortName: "SoundCloud", online: false, linked: false },
    { id: "youtube", code: "YT", name: "YouTube", shortName: "YouTube", online: false, linked: false },
];

export const linkHints: Record<string, string> = {
    yandex: "Откройте страницу Яндекса, войдите в свой аккаунт и введите этот код.",
    spotify: "Войдите в Spotify в новой вкладке — привязка завершится сама.",
    soundcloud: "Войдите в SoundCloud в новой вкладке — привязка завершится сама.",
    youtube: "Войдите в аккаунт Google в новой вкладке — привязка завершится сама.",
};

export function getServiceName(idOrCode: string) {
    if (idOrCode === "local" || idOrCode === "ФАЙЛ") {
        return "Моя музыка";
    }
    const service = defaultServices.find((item) => item.id === idOrCode || item.code === idOrCode);
    return service ? service.name : idOrCode;
}
