import type { Service } from "../types.ts";

export const defaultServices: Service[] = [
    { id: "yandex", code: "ЯМ", name: "Яндекс Музыка", shortName: "Яндекс", online: false, linked: false },
    { id: "youtube", code: "YT", name: "YouTube", shortName: "YouTube", online: false, linked: false },
    { id: "vk", code: "VK", name: "VK Музыка", shortName: "VK", online: false, linked: false },
];

export const deviceLinkServices = ["yandex", "youtube"];

export const deviceLinkHints: Record<string, string> = {
    yandex: "Откройте страницу Яндекса, войдите в аккаунт и введите этот код. Привязка завершится сама.",
    youtube: "Откройте страницу Google, войдите в аккаунт и введите этот код. Привязка завершится сама.",
};

export function getServiceName(idOrCode: string) {
    if (idOrCode === "local" || idOrCode === "ФАЙЛ") {
        return "Моя музыка";
    }
    const service = defaultServices.find((item) => item.id === idOrCode || item.code === idOrCode);
    return service ? service.name : idOrCode;
}
