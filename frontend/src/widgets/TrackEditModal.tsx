import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { readTagsFromUrl } from "../shared/audioTags.ts";
import { saveTrackInfo } from "../shared/library.ts";
import { coverTemplates, fallbackCover } from "../shared/coverTemplates.ts";
import type { UserFile } from "../shared/types.ts";
import CloseIcon from "../shared/icons/close.svg?react";
import UploadIcon from "../shared/icons/upload.svg?react";
import EditorIcon from "../shared/icons/editor.svg?react";

type TrackEditModalProps = {
    file: UserFile
    onSaved: (file: UserFile) => void
    onClose: () => void
}

function TrackEditModal({ file, onSaved, onClose }: TrackEditModalProps) {
    const [title, setTitle] = useState(file.name);
    const [artist, setArtist] = useState(file.artist);
    const [cover, setCover] = useState<Blob | number | undefined>(undefined);
    const [coverPreview, setCoverPreview] = useState(file.cover || fallbackCover(file.id));
    const [note, setNote] = useState("");
    const [error, setError] = useState("");
    const [isBusy, setIsBusy] = useState(false);
    const [isClosing, setIsClosing] = useState(false);
    const imageInput = useRef<HTMLInputElement>(null);

    const selectedTemplate = coverTemplates.indexOf(coverPreview);

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

    useEffect(() => {
        return () => {
            if (coverPreview.startsWith("blob:")) {
                URL.revokeObjectURL(coverPreview);
            }
        };
    }, [coverPreview]);

    function chooseImage(image: Blob) {
        setCover(image);
        setCoverPreview(URL.createObjectURL(image));
    }

    function chooseTemplate(index: number) {
        setCover(index);
        setCoverPreview(coverTemplates[index]);
    }

    async function fillFromFile() {
        setIsBusy(true);
        setError("");
        setNote("");
        try {
            const tags = await readTagsFromUrl(file.audioUrl);
            if (!tags.title && !tags.artist && !tags.cover) {
                setNote("В файле нет данных о треке — заполните вручную");
            } else {
                if (tags.title) {
                    setTitle(tags.title);
                }
                if (tags.artist) {
                    setArtist(tags.artist);
                }
                if (tags.cover) {
                    chooseImage(tags.cover);
                }
                setNote("Данные взяты из файла — проверьте и сохраните");
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Не удалось прочитать файл");
        }
        setIsBusy(false);
    }

    async function handleSubmit(event: FormEvent) {
        event.preventDefault();
        if (title.trim() === "") {
            setError("Введите название");
            return;
        }

        setIsBusy(true);
        setError("");
        try {
            const saved = await saveTrackInfo(file, {
                title: title.trim(),
                artist: artist.trim() || "Моя музыка",
                cover: cover,
            });
            onSaved(saved);
            closeModal();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Не удалось сохранить");
            setIsBusy(false);
        }
    }

    return (
        <div className={isClosing ? "modal-overlay closing" : "modal-overlay"} onMouseDown={closeModal}>
            <form className="modal track-edit" onMouseDown={(event) => event.stopPropagation()} onSubmit={handleSubmit}>
                <div className="track-edit-header">
                    <div className="track-edit-heading">
                        <h2>Редактировать трек</h2>
                    </div>
                    <button type="button" className="track-edit-close" title="Закрыть" onClick={closeModal}>
                        <CloseIcon width={20} height={20}/>
                    </button>
                </div>

                <div className="track-edit-main">
                    <div className="track-edit-side">
                        <div className="track-edit-cover">
                            <img src={coverPreview} alt=""/>
                        </div>
                        <button type="button" className="track-edit-upload" onClick={() => imageInput.current?.click()}>
                            <UploadIcon width={18} height={18}/>
                            Своя картинка
                        </button>
                        <input
                            ref={imageInput}
                            type="file"
                            accept="image/*"
                            hidden
                            onChange={(event) => {
                                const image = event.target.files?.[0];
                                if (image) {
                                    chooseImage(image);
                                }
                                event.target.value = "";
                            }}
                        />
                    </div>

                    <div className="track-edit-fields">
                        <div>
                            <div className="label track-edit-templates-title">ШАБЛОННАЯ ОБЛОЖКА</div>
                            <div className="track-edit-templates">
                                {coverTemplates.map((template, index) => (
                                    <button
                                        key={template}
                                        type="button"
                                        className={index === selectedTemplate ? "track-edit-template selected" : "track-edit-template"}
                                        title={"Шаблон " + (index + 1)}
                                        onClick={() => chooseTemplate(index)}
                                    >
                                        <img src={template} alt=""/>
                                    </button>
                                ))}
                            </div>
                        </div>

                        <label className="auth-field">
                            <span className="label">НАЗВАНИЕ</span>
                            <input value={title} onChange={(event) => setTitle(event.target.value)}/>
                        </label>
                        <label className="auth-field">
                            <span className="label">АВТОР</span>
                            <input value={artist} onChange={(event) => setArtist(event.target.value)}/>
                        </label>

                        <button type="button" className="link-plain section-link track-edit-fill" disabled={isBusy} onClick={fillFromFile}>
                            ПОДТЯНУТЬ ИЗ ФАЙЛА
                        </button>
                    </div>
                </div>

                {note && <p className="search-note">{note}</p>}
                {error && <p className="auth-error">{error}</p>}

                <div className="track-edit-footer">
                    <a className="track-edit-effects" href="#" title="Редактор скоро появится" onClick={(event) => event.preventDefault()}>
                        <EditorIcon width={16} height={16}/>
                        ОБРЕЗКА И ЭФФЕКТЫ →
                    </a>
                    <div className="track-edit-actions">
                        <button type="button" className="button outline-light track-edit-button" onClick={closeModal}>
                            Отмена
                        </button>
                        <button type="submit" className="button accent track-edit-button" disabled={isBusy}>
                            {isBusy ? "Подождите…" : "Сохранить"}
                        </button>
                    </div>
                </div>
            </form>
        </div>
    )
}

export default TrackEditModal
