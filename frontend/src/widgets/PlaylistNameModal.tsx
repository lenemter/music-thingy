import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import CloseIcon from "../shared/icons/close.svg?react";

type PlaylistNameModalProps = {
    title: string
    submitText: string
    initialName?: string
    note?: string
    onSubmit: (name: string) => void
    onClose: () => void
    // Вызывается вместо onClose, если окно закрыли без сохранения (Отмена, крестик, Escape, клик мимо).
    onCancel?: () => void
}

function PlaylistNameModal({ title, submitText, initialName = "", note, onSubmit, onClose, onCancel }: PlaylistNameModalProps) {
    const [name, setName] = useState(initialName);
    const [error, setError] = useState("");
    const [isClosing, setIsClosing] = useState(false);

    function closeModal(isSaved = false) {
        if (isClosing) {
            return;
        }
        setIsClosing(true);
        setTimeout(isSaved || !onCancel ? onClose : onCancel, 200);
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

    function handleSubmit(event: FormEvent) {
        event.preventDefault();
        const value = name.trim();
        if (value === "") {
            setError("Введите название");
            return;
        }
        if (value.length > 80) {
            setError("Название длиннее 80 символов");
            return;
        }
        try {
            onSubmit(value);
            closeModal(true);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Не удалось сохранить");
        }
    }

    return (
        <div className={isClosing ? "modal-overlay closing" : "modal-overlay"} onMouseDown={() => closeModal()}>
            <form className="modal playlist-modal" onMouseDown={(event) => event.stopPropagation()} onSubmit={handleSubmit}>
                <div className="track-edit-header">
                    <h2>{title}</h2>
                    <button type="button" className="track-edit-close" title="Закрыть" onClick={() => closeModal()}>
                        <CloseIcon width={20} height={20}/>
                    </button>
                </div>
                {note && <p className="modal-text">{note}</p>}
                <label className="auth-field">
                    <span className="label">НАЗВАНИЕ</span>
                    <input autoFocus value={name} placeholder="Например, «Ночные поездки»" onChange={(event) => setName(event.target.value)}/>
                </label>
                {error && <p className="auth-error">{error}</p>}
                <div className="track-edit-actions">
                    <button type="button" className="button outline-light track-edit-button" onClick={() => closeModal()}>Отмена</button>
                    <button type="submit" className="button accent track-edit-button">{submitText}</button>
                </div>
            </form>
        </div>
    )
}

export default PlaylistNameModal
