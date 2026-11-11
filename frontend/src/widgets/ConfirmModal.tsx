import { useEffect, useRef, useState } from "react";
import { rememberSkip, subscribeConfirm } from "../shared/confirm.ts";
import type { ConfirmIcon, ConfirmRequest } from "../shared/confirm.ts";

const iconPaths: Record<ConfirmIcon, string> = {
    delete: "M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6",
    logout: "M10 4H5v16h5M14 8l5 4-5 4M19 12H9",
    reset: "M4 7h16M4 12h16M4 17h16",
    disconnect: "M12 11v10M8 21l4-10 4 10M6.3 6.3a8 8 0 0 1 11.4 0",
};

function ConfirmDialog({ request, onDone }: { request: ConfirmRequest, onDone: () => void }) {
    const [isClosing, setIsClosing] = useState(false);
    const [dontAsk, setDontAsk] = useState(false);
    const cancelButton = useRef<HTMLButtonElement>(null);
    const confirmButton = useRef<HTMLButtonElement>(null);
    const icon = request.icon ?? (request.danger ? "delete" : "logout");

    function finish(result: boolean) {
        if (isClosing) {
            return;
        }
        if (result && dontAsk && request.rememberKey) {
            rememberSkip(request.rememberKey);
        }
        request.resolve(result);
        setIsClosing(true);
        setTimeout(onDone, 200);
    }

    // В опасных действиях фокус на «Отмене», чтобы случайный Enter ничего не удалил.
    useEffect(() => {
        (request.danger ? cancelButton : confirmButton).current?.focus();
    }, [request.danger]);

    useEffect(() => {
        // Перехватываем Escape раньше остальных окон, чтобы не закрылось окно под подтверждением.
        function handleKey(event: KeyboardEvent) {
            if (event.key === "Escape") {
                event.stopPropagation();
                finish(false);
            }
        }
        window.addEventListener("keydown", handleKey, true);
        return () => window.removeEventListener("keydown", handleKey, true);
    });

    return (
        <div className={isClosing ? "modal-overlay confirm-overlay closing" : "modal-overlay confirm-overlay"} onMouseDown={() => finish(false)}>
            <div
                className={request.danger ? "modal confirm danger" : "modal confirm"}
                role="alertdialog"
                aria-modal="true"
                aria-labelledby="confirm-title"
                aria-describedby="confirm-text"
                onMouseDown={(event) => event.stopPropagation()}
            >
                <div className="confirm-main">
                    <span className="confirm-icon">
                        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                            <path d={iconPaths[icon]}/>
                        </svg>
                    </span>
                    <div className="confirm-body">
                        <h2 id="confirm-title">{request.title}</h2>
                        <p id="confirm-text">{request.text}</p>
                    </div>
                </div>

                {request.details && request.details.length > 0 && (
                    <ul className="confirm-details">
                        {request.details.map((detail) => (
                            <li key={detail.label}>
                                <span>{detail.label}</span>
                                <span className={detail.accent ? "accent" : ""}>{detail.value}</span>
                            </li>
                        ))}
                    </ul>
                )}

                {request.rememberKey && (
                    <label className="confirm-option">
                        <input type="checkbox" checked={dontAsk} onChange={(event) => setDontAsk(event.target.checked)}/>
                        Больше не спрашивать
                    </label>
                )}

                <div className="confirm-actions">
                    <button ref={cancelButton} type="button" className="confirm-button" onClick={() => finish(false)}>Отмена</button>
                    <button
                        ref={confirmButton}
                        type="button"
                        className={request.danger ? "confirm-button danger" : "confirm-button primary"}
                        onClick={() => finish(true)}
                    >
                        {request.confirmText}
                    </button>
                </div>
            </div>
        </div>
    )
}

function ConfirmModal() {
    const [requests, setRequests] = useState<ConfirmRequest[]>([]);

    useEffect(() => subscribeConfirm((request) => setRequests((list) => [...list, request])), []);

    const current = requests[0];
    if (!current) {
        return null;
    }
    return (
        <ConfirmDialog
            key={current.id}
            request={current}
            onDone={() => setRequests((list) => list.slice(1))}
        />
    )
}

export default ConfirmModal
