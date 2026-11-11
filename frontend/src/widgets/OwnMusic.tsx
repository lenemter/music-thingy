import { useRef, useState } from "react";
import { confirmAction } from "../shared/confirm.ts";
import type { DragEvent } from "react";
import { formatTime } from "../shared/format.ts";
import { deleteUpload } from "../shared/library.ts";
import { fallbackCover } from "../shared/coverTemplates.ts";
import { AUDIO_ACCEPT, useUploader } from "../shared/useUploader.ts";
import type { UserFile } from "../shared/types.ts";
import UploadIcon from "../shared/icons/upload.svg?react";
import CloseIcon from "../shared/icons/close.svg?react";
import Equalizer from "../entities/Equalizer.tsx";
import sunStar from "../shared/images/sun-star.svg";

type OwnMusicProps = {
    files: UserFile[]
    playingFileId: number | null
    onFilesChange: (files: UserFile[]) => void
    onPlay: (file: UserFile) => void
    onDeleted: (file: UserFile) => void
    onOpenLibrary: () => void
}

const VISIBLE_COUNT = 4;

function OwnMusic({ files, playingFileId, onFilesChange, onPlay, onDeleted, onOpenLibrary }: OwnMusicProps) {
    const uploader = useUploader(files, onFilesChange);
    const [isDragOver, setIsDragOver] = useState(false);
    const [deleteError, setDeleteError] = useState("");
    const inputRef = useRef<HTMLInputElement>(null);

    const visibleFiles = files.slice(0, VISIBLE_COUNT);

    function handleDrop(event: DragEvent) {
        event.preventDefault();
        setIsDragOver(false);
        uploader.uploadFiles(Array.from(event.dataTransfer.files));
    }

    async function handleDelete(file: UserFile) {
        const isConfirmed = await confirmAction({
            title: "Удалить «" + file.name + "»?",
            text: "Файл и его правки удалятся из этого браузера навсегда. Восстановить не получится.",
            confirmText: "Удалить",
            danger: true,
            icon: "delete",
        });
        if (!isConfirmed) {
            return;
        }
        setDeleteError("");
        try {
            await deleteUpload(file.id);
            onDeleted(file);
            onFilesChange(files.filter((item) => item.id !== file.id));
        } catch (err) {
            setDeleteError(file.name + ": " + (err instanceof Error ? err.message : "не удалось удалить"));
        }
    }

    return (
        <section
            className={isDragOver ? "section own-music drag-over" : "section own-music"}
            onDragOver={(event) => {
                event.preventDefault();
                setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
        >
            <img className="own-music-star" src={sunStar} alt=""/>

            <h2>Своя музыка</h2>
            <p>
                Загрузите MP3, FLAC или WAV — или перетащите файлы сюда. Название, исполнитель и обложка подтянутся из файла.
            </p>

            <input
                ref={inputRef}
                type="file"
                accept={AUDIO_ACCEPT}
                multiple
                hidden
                onChange={(event) => {
                    uploader.uploadFiles(Array.from(event.target.files ?? []));
                    event.target.value = "";
                }}
            />
            <button className="button accent" disabled={uploader.isUploading} onClick={() => inputRef.current?.click()}>
                <UploadIcon width={18} height={18}/>
                {uploader.isUploading ? "Загружаем…" : "Загрузить файлы"}
            </button>

            {uploader.status && <p className="search-note">{uploader.status}</p>}
            {[...uploader.errors, deleteError].filter(Boolean).map((error) => (
                <p key={error} className="auth-error">{error}</p>
            ))}

            {files.length > 0 ? (
                <ul className="files">
                    {visibleFiles.map((file) => (
                        <li
                            key={file.id}
                            className={file.id === playingFileId ? "file playing" : "file"}
                            title={"Слушать «" + file.name + "»"}
                            onClick={() => onPlay(file)}
                        >
                            {file.id === playingFileId ? (
                                <span className="file-type"><Equalizer/></span>
                            ) : (
                                <img className="file-type file-cover" src={file.cover || fallbackCover(file.id)} alt=""/>
                            )}
                            <span className="file-info">
                                <span className="file-name">{file.name}</span>
                                <span className="mono">{file.artist} · {formatTime(file.duration)}</span>
                            </span>
                            <button
                                className="icon-button file-delete"
                                title="Удалить файл"
                                onClick={(event) => {
                                    event.stopPropagation();
                                    handleDelete(file);
                                }}
                            >
                                <CloseIcon width={16} height={16}/>
                            </button>
                        </li>
                    ))}
                </ul>
            ) : (
                !uploader.isUploading && <p className="search-note files-empty">Пока пусто — загрузите первый трек.</p>
            )}

            {files.length > 0 && (
                <button className="section-link link-plain own-music-more" onClick={onOpenLibrary}>
                    {files.length > VISIBLE_COUNT ? "ВСЕ " + files.length + " В МЕДИАТЕКЕ →" : "ОТКРЫТЬ МЕДИАТЕКУ →"}
                </button>
            )}
        </section>
    )
}

export default OwnMusic
