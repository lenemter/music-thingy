import { useEffect, useRef, useState } from "react";
import { confirmAction } from "../shared/confirm.ts";
import ServiceLink from "./ServiceLink.tsx";
import { ApiError, disconnectService, fetchServices, setServiceActive, startDeviceLink } from "../shared/api.ts";
import { deviceLinkServices } from "../shared/music/services.ts";
import type { DeviceCode, ServiceId } from "../shared/music/types.ts";
import type { Service } from "../shared/types.ts";
import CloseIcon from "../shared/icons/close.svg?react";

type SourcesModalProps = {
    services: Service[]
    onUpdate: (services: Service[]) => void
    onClose: () => void
}

function getLinkError(err: unknown) {
    if (err instanceof ApiError && (err.status === 404 || err.status === 405)) {
        return "Сервер пока не поддерживает привязку аккаунтов";
    }
    return err instanceof Error ? err.message : "Не удалось начать вход";
}

function SourcesModal({ services, onUpdate, onClose }: SourcesModalProps) {
    const [error, setError] = useState("");
    const [loadingService, setLoadingService] = useState<ServiceId | null>(null);
    const [isClosing, setIsClosing] = useState(false);
    const [linkingService, setLinkingService] = useState<Service | null>(null);
    const [deviceCode, setDeviceCode] = useState<DeviceCode | null>(null);
    const [isStarting, setIsStarting] = useState(false);
    const linkAttempt = useRef(0);

    function closeModal() {
        if (isClosing) {
            return;
        }
        setIsClosing(true);
        setTimeout(onClose, 200);
    }

    useEffect(() => {
        function handleKey(event: KeyboardEvent) {
            if (event.key === "Escape") {
                closeModal();
            }
        }
        document.addEventListener("keydown", handleKey);
        return () => document.removeEventListener("keydown", handleKey);
    });

    async function toggleService(service: Service) {
        setLoadingService(service.id);
        setError("");
        try {
            onUpdate(await setServiceActive(service.id, !service.online));
        } catch (err) {
            setError(err instanceof Error ? err.message : "Не удалось сохранить");
        }
        setLoadingService(null);
    }

    async function startLink(service: Service) {
        linkAttempt.current++;
        const attempt = linkAttempt.current;
        setLinkingService(service);
        setDeviceCode(null);
        setError("");
        const usesCode = deviceLinkServices.includes(service.id);
        setIsStarting(usesCode);
        if (!usesCode) {
            return;
        }
        try {
            const code = await startDeviceLink(service.id);
            if (attempt === linkAttempt.current) {
                setDeviceCode(code);
            }
        } catch (err) {
            if (attempt === linkAttempt.current) {
                setLinkingService(null);
                setError(getLinkError(err));
            }
        }
        if (attempt === linkAttempt.current) {
            setIsStarting(false);
        }
    }

    function cancelLink() {
        linkAttempt.current++;
        setLinkingService(null);
        setDeviceCode(null);
        setIsStarting(false);
    }

    async function handleLinked() {
        cancelLink();
        try {
            onUpdate(await fetchServices());
        } catch {
            setError("Аккаунт привязан, но не удалось обновить список");
        }
    }

    async function handleUnlink(service: Service) {
        const isConfirmed = await confirmAction({
            title: "Отвязать сервис " + service.name + "?",
            text: "Его треки перестанут играть, а плейлисты из него станут недоступны. Подключить снова можно в любой момент.",
            confirmText: "Отвязать",
            danger: true,
            icon: "disconnect",
            details: [
                ...(service.accountName ? [{ label: "Аккаунт", value: service.accountName }] : []),
                { label: "Свои плейлисты и лайки", value: "сохранятся", accent: true },
            ],
        });
        if (!isConfirmed) {
            return;
        }
        setLoadingService(service.id);
        setError("");
        try {
            await disconnectService(service.id);
            onUpdate(await fetchServices());
        } catch (err) {
            setError(getLinkError(err));
        }
        setLoadingService(null);
    }

    return (
        <div className={isClosing ? "modal-overlay closing" : "modal-overlay"} onMouseDown={closeModal}>
            <div className="modal" onMouseDown={(event) => event.stopPropagation()}>
                <div className="track-edit-header">
                    <div className="track-edit-heading"><h2>Источники</h2></div>
                    <button type="button" className="track-edit-close" title="Закрыть" aria-label="Закрыть" onClick={closeModal}>
                        <CloseIcon width={20} height={20}/>
                    </button>
                </div>
                <p className="modal-text">
                    Привяжите свои аккаунты, чтобы слушать музыку из своих подписок. Включать и выключать сервисы в поиске можно кнопками в строке поиска.
                </p>

                <ul className="source-list">
                    {services.map((service) => (
                        <li key={service.id} className="source-item">
                            <span className={service.online ? "tag active" : "tag"}>{service.code}</span>
                            <span className="source-item-info">
                                <span className="source-item-name">{service.name}</span>
                                <span className="mono">
                                    {service.linked ? (service.accountName ?? "ваш аккаунт") + " · " + (service.online ? "включён" : "выключен") : "не привязан"}
                                </span>
                            </span>

                            {service.linked ? (
                                <button
                                    className="button outline-light small"
                                    disabled={loadingService !== null}
                                    onClick={() => handleUnlink(service)}
                                >
                                    Отвязать
                                </button>
                            ) : (
                                <button
                                    className={linkingService?.id === service.id ? "button accent small" : "button outline-light small"}
                                    onClick={() => startLink(service)}
                                >
                                    Привязать
                                </button>
                            )}

                            {service.linked && (
                                <button
                                    className={service.online ? "switch on" : "switch"}
                                    title={service.online ? "Выключить" : "Включить"}
                                    disabled={loadingService !== null}
                                    onClick={() => toggleService(service)}
                                >
                                    <span className="switch-knob"/>
                                </button>
                            )}
                        </li>
                    ))}
                </ul>

                {linkingService !== null && isStarting && (
                    <p className="modal-text">Готовим вход…</p>
                )}

                {linkingService !== null && !isStarting && (!deviceLinkServices.includes(linkingService.id) || deviceCode !== null) && (
                    <ServiceLink
                        key={linkingService.id + (deviceCode?.device_code ?? "")}
                        service={linkingService}
                        deviceCode={deviceCode}
                        onLinked={handleLinked}
                        onRestart={() => startLink(linkingService)}
                        onCancel={cancelLink}
                    />
                )}

                {error && <p className="auth-error">{error}</p>}
            </div>
        </div>
    )
}

export default SourcesModal
