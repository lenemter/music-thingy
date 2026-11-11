import { useEffect, useState } from "react";
import { getServiceLinkStatus } from "../shared/api.ts";
import { linkHints } from "../shared/music/services.ts";
import type { LinkStartResponse } from "../shared/music/types.ts";
import type { Service } from "../shared/types.ts";

type ServiceLinkProps = {
    service: Service
    session: LinkStartResponse
    onLinked: () => void
    onRestart: () => void
    onCancel: () => void
}

function ServiceLink({ service, session, onLinked, onRestart, onCancel }: ServiceLinkProps) {
    const [error, setError] = useState("");
    const [isFinished, setIsFinished] = useState(false);
    const [isCopied, setIsCopied] = useState(false);

    useEffect(() => {
        if (isFinished) {
            return;
        }

        const timer = setInterval(async () => {
            try {
                const result = await getServiceLinkStatus(service.id, session.session_id);

                if (result.status === "linked") {
                    setIsFinished(true);
                    onLinked();
                }
                if (result.status === "expired") {
                    setIsFinished(true);
                    setError("Время на вход истекло");
                }
                if (result.status === "denied") {
                    setIsFinished(true);
                    setError(result.detail ?? "Вход отклонён");
                }
            } catch (err) {
                setIsFinished(true);
                setError(err instanceof Error ? err.message : "Не удалось проверить вход");
            }
        }, Math.max(session.interval, 2) * 1000);

        return () => clearInterval(timer);
    }, [session, isFinished, service.id, onLinked]);

    async function copyCode() {
        if (!session.user_code) {
            return;
        }
        try {
            await navigator.clipboard.writeText(session.user_code);
            setIsCopied(true);
        } catch {
            setIsCopied(false);
        }
    }

    return (
        <div className="source-form">
            <span className="label">ПРИВЯЗКА · {service.name.toUpperCase()}</span>

            {!isFinished && (
                <>
                    <p className="modal-text">{linkHints[service.id]}</p>

                    {session.kind === "device_code" && session.user_code && (
                        <div className="device-code">
                            <span className="device-code-value">{session.user_code}</span>
                            <button className="link-plain section-link" onClick={copyCode}>
                                {isCopied ? "СКОПИРОВАНО" : "СКОПИРОВАТЬ"}
                            </button>
                        </div>
                    )}

                    <button
                        className="button accent auth-submit"
                        onClick={() => window.open(session.url, "_blank", "noopener")}
                    >
                        Открыть страницу входа
                    </button>
                    <p className="search-note">Ждём подтверждения…</p>
                </>
            )}

            {error && <p className="auth-error">{error}</p>}

            <div className="source-form-actions">
                {isFinished && error && (
                    <button className="button accent small" onClick={onRestart}>Попробовать снова</button>
                )}
                <button className="button outline-light small" onClick={onCancel}>Отмена</button>
            </div>
        </div>
    )
}

export default ServiceLink
