import { useRef, useState } from "react";
import type { DragEvent } from "react";
import Header from "../widgets/Header.tsx";
import TrackEditModal from "../widgets/TrackEditModal.tsx";
import Equalizer from "../entities/Equalizer.tsx";
import { deleteUpload } from "../shared/api.ts";
import { formatTime } from "../shared/format.ts";
import { removeOverride } from "../shared/library.ts";
import { AUDIO_ACCEPT, useUploader } from "../shared/useUploader.ts";
import type { Service, User, UserFile } from "../shared/types.ts";
import UploadIcon from "../shared/icons/upload.svg?react";
import PencilIcon from "../shared/icons/pencil.svg?react";
import CloseIcon from "../shared/icons/close.svg?react";
import { fallbackCover } from "../shared/coverTemplates.ts";

type LibraryPageProps = {
    user: User
    services: Service[]
    files: UserFile[]
    playingFileId: number | null
    onFilesChange: (files: UserFile[]) => void
    onPlay: (file: UserFile) => void
    onDeleted: (file: UserFile) => void
    onLogout: () => void
    onSearch: (query: string) => void
    onServicesChange: (services: Service[]) => void
}

function trackWord(count: number) {
    const lastTwo = count % 100;
    const last = count % 10;
    if (lastTwo >= 11 && lastTwo <= 14) {
        return "треков";
    }
    if (last === 1) {
        return "трек";
    }
    if (last >= 2 && last <= 4) {
        return "трека";
    }
    return "треков";
}

function LibraryPage(props: LibraryPageProps) {
    const { user, services, files, playingFileId, onFilesChange, onPlay, onDeleted } = props;
    const { onLogout, onSearch, onServicesChange } = props;
    const uploader = useUploader(files, onFilesChange);
    const [editingFile, setEditingFile] = useState<UserFile | null>(null);
    const [isDragOver, setIsDragOver] = useState(false);
    const [notice, setNotice] = useState("");
    const [deleteError, setDeleteError] = useState("");
    const inputRef = useRef<HTMLInputElement>(null);

    function handleDrop(event: DragEvent) {
        event.preventDefault();
        setIsDragOver(false);
        uploader.uploadFiles(Array.from(event.dataTransfer.files));
    }

    async function handleDelete(file: UserFile) {
        if (!window.confirm("Удалить «" + file.name + "»? Файл удалится без возможности восстановления.")) {
            return;
        }
        setDeleteError("");
        try {
            await deleteUpload(file.id);
            removeOverride(file.id);
            onDeleted(file);
            onFilesChange(files.filter((item) => item.id !== file.id));
        } catch (err) {
            setDeleteError(file.name + ": " + (err instanceof Error ? err.message : "не удалось удалить"));
        }
    }

    function handleSaved(updated: UserFile, savedLocally: boolean) {
        onFilesChange(files.map((item) => (item.id === updated.id ? updated : item)));
        setNotice(savedLocally ? "Изменения сохранены в этом браузере — сервер пока не умеет их хранить" : "");
    }

    return (
        <main
            className="main"
            onDragOver={(event) => {
                event.preventDefault();
                setIsDragOver(true);
            }}
            onDragLeave={(event) => {
                if (event.currentTarget === event.target) {
                    setIsDragOver(false);
                }
            }}
            onDrop={handleDrop}
        >
            <Header user={user} services={services} onLogout={onLogout} onSearch={onSearch} onServicesChange={onServicesChange}/>

            <section className={isDragOver ? "section library drag-over" : "section library"}>
                <div className="library-header">
                    <div>
                        <h1 className="library-title">Медиатека</h1>
                        <span className="mono">{files.length} {trackWord(files.length)}</span>
                    </div>
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
                        {uploader.isUploading ? "Загружаем…" : "Загрузить музыку"}
                    </button>
                </div>

                {uploader.status && <p className="search-note">{uploader.status}</p>}
                {notice && <p className="search-note">{notice}</p>}
                {[...uploader.errors, deleteError].filter(Boolean).map((error) => (
                    <p key={error} className="auth-error">{error}</p>
                ))}

                {files.length === 0 && !uploader.isUploading && (
                    <div className="library-empty">
                        <p>Здесь будет ваша музыка. Загрузите MP3, FLAC, WAV, OGG, M4A или AAC — название, исполнитель и обложка подтянутся из файла.</p>
                    </div>
                )}

                {files.length > 0 && (
                    <ol className="track-list">
                        {files.map((file, index) => (
                            <li
                                key={file.id}
                                className={file.id === playingFileId ? "track playing" : "track"}
                                onClick={() => onPlay(file)}
                            >
                                {file.id === playingFileId ? (
                                    <Equalizer/>
                                ) : (
                                    <span className="track-number">{index + 1 < 10 ? "0" + (index + 1) : index + 1}</span>
                                )}
                                <span className="cover row">
                                    <img src={file.cover || fallbackCover(file.id)} alt=""/>
                                </span>
                                <span className="track-info">
                                    <span className="track-title">{file.name}</span>
                                    <span className="track-artist">{file.artist}</span>
                                </span>
                                <span className="tags"><span className="tag">{file.type}</span></span>
                                <span className="mono track-time">{formatTime(file.duration)}</span>
                                <span className="mono library-size">{file.size} МБ</span>
                                <button
                                    className="icon-button"
                                    title="Изменить название, исполнителя и обложку"
                                    onClick={(event) => {
                                        event.stopPropagation();
                                        setEditingFile(file);
                                    }}
                                >
                                    <PencilIcon/>
                                </button>
                                <button
                                    className="icon-button file-delete"
                                    title="Удалить"
                                    onClick={(event) => {
                                        event.stopPropagation();
                                        handleDelete(file);
                                    }}
                                >
                                    <CloseIcon width={16} height={16}/>
                                </button>
                            </li>
                        ))}
                    </ol>
                )}
            </section>

            {editingFile && (
                <TrackEditModal
                    file={editingFile}
                    onSaved={handleSaved}
                    onClose={() => setEditingFile(null)}
                />
            )}
        </main>
    )
}

export default LibraryPage
