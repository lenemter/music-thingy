import { useEffect, useState } from "react";
import ServiceLink from "./ServiceLink.tsx";
import { ApiError, fetchServices, startServiceLink, unlinkService, updateServicePreferences } from "../shared/api.ts";
import type { LinkStartResponse, ServiceId } from "../shared/music/types.ts";
import type { Service } from "../shared/types.ts";

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
    const [session, setSession] = useState<LinkStartResponse | null>(null);

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
        const enabled = services.filter((item) => item.online).map((item) => item.id);
        const newEnabled = service.online
            ? enabled.filter((id) => id !== service.id)
            : [...enabled, service.id];

        setLoadingService(service.id);
        setError("");
        try {
            const updated = await updateServicePreferences(newEnabled);
            onUpdate(updated);

            const result = updated.find((item) => item.id === service.id);
            if (!service.online && result && !result.online) {
                setError(service.name + " пока не настроен на сервере — привяжите свой аккаунт");
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Не удалось сохранить");
        }
        setLoadingService(null);
    }

    async function startLink(service: Service) {
        setLinkingService(service);
        setSession(null);
        setError("");
        try {
            setSession(await startServiceLink(service.id));
        } catch (err) {
            setLinkingService(null);
            setError(getLinkError(err));
        }
    }

    function cancelLink() {
        setLinkingService(null);
        setSession(null);
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
        setLoadingService(service.id);
        setError("");
        try {
            await unlinkService(service.id);
            onUpdate(await fetchServices());
        } catch (err) {
            setError(getLinkError(err));
        }
        setLoadingService(null);
    }

    return (
        <div className={isClosing ? "modal-overlay closing" : "modal-overlay"} onMouseDown={closeModal}>
            <div className="modal" onMouseDown={(event) => event.stopPropagation()}>
                <div className="modal-header">
                    <h2>Источники</h2>
                    <button className="section-link" onClick={closeModal}>ЗАКРЫТЬ</button>
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
                                    {service.linked ? "ваш аккаунт · " + (service.online ? "включён" : "выключен") : "не привязан"}
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
                                    className="button outline-light small"
                                    disabled={loadingService !== null || linkingService !== null}
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

                {linkingService !== null && session === null && (
                    <p className="modal-text">Готовим вход…</p>
                )}

                {linkingService !== null && session !== null && (
                    <ServiceLink
                        key={session.session_id}
                        service={linkingService}
                        session={session}
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
