import { useRef, useState } from "react";
import { confirmAction } from "../shared/confirm.ts";
import type { DragEvent } from "react";
import Header from "../widgets/Header.tsx";
import TrackEditModal from "../widgets/TrackEditModal.tsx";
import Equalizer from "../entities/Equalizer.tsx";
import { formatTime } from "../shared/format.ts";
import { deleteUpload } from "../shared/library.ts";
import { AUDIO_ACCEPT, useUploader } from "../shared/useUploader.ts";
import type { Service, User, UserFile } from "../shared/types.ts";
import UploadIcon from "../shared/icons/upload.svg?react";
import PencilIcon from "../shared/icons/pencil.svg?react";
import CloseIcon from "../shared/icons/close.svg?react";
import { fallbackCover } from "../shared/coverTemplates.ts";
import PlaylistCover, { NoteIcon } from "../entities/PlaylistCover.tsx";
import PlaylistView from "../widgets/PlaylistView.tsx";
import LikeButton from "../entities/LikeButton.tsx";
import { plural, trackCount } from "../shared/format.ts";
import { openAddToPlaylist } from "../shared/playlists.ts";
import { trackFromFile } from "../shared/music/convert.ts";
import type { LibraryPlaylist } from "../shared/usePlaylists.ts";
import type { Track } from "../shared/types.ts";
import PlusIcon from "../shared/icons/plus.svg?react";

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
    playlists: LibraryPlaylist[]
    isLoadingPlaylists: boolean
    openPlaylistId: string | null
    currentTrackId: string | null
    onOpenPlaylist: (id: string | null) => void
    onCreatePlaylist: () => void
    onRenamePlaylist: (playlist: LibraryPlaylist) => void
    onDeletePlaylist: (playlist: LibraryPlaylist) => void
    onPlayTrack: (track: Track, queue: Track[]) => void
    onOpenSources: () => void
}

function LibraryPage(props: LibraryPageProps) {
    const { user, services, files, playingFileId, onFilesChange, onPlay, onDeleted } = props;
    const { onLogout, onSearch, onServicesChange } = props;
    const { playlists, isLoadingPlaylists, openPlaylistId, currentTrackId } = props;
    const { onOpenPlaylist, onCreatePlaylist, onRenamePlaylist, onDeletePlaylist, onPlayTrack, onOpenSources } = props;
    const openPlaylist = playlists.find((playlist) => playlist.id === openPlaylistId) ?? null;
    const hasServicePlaylists = playlists.some((playlist) => playlist.kind === "service");
    const uploader = useUploader(files, onFilesChange);
    const [editingFile, setEditingFile] = useState<UserFile | null>(null);
    const [isDragOver, setIsDragOver] = useState(false);
    const [deleteError, setDeleteError] = useState("");
    const inputRef = useRef<HTMLInputElement>(null);

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

    function handleSaved(updated: UserFile) {
        onFilesChange(files.map((item) => (item.id === updated.id ? updated : item)));
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

            {openPlaylist ? (
                <PlaylistView
                    key={openPlaylist.id}
                    playlist={openPlaylist}
                    services={services}
                    currentTrackId={currentTrackId}
                    onPlay={onPlayTrack}
                    onBack={() => onOpenPlaylist(null)}
                    onRename={() => onRenamePlaylist(openPlaylist)}
                    onDelete={() => onDeletePlaylist(openPlaylist)}
                    onOpenSources={onOpenSources}
                />
            ) : (
            <section className={isDragOver ? "section library drag-over" : "section library"}>
                <div className="library-header">
                    <div>
                        <h1 className="library-title">Медиатека</h1>
                        <span className="mono">{playlists.length} {plural(playlists.length, "плейлист", "плейлиста", "плейлистов")} · {trackCount(files.length)} в загрузках</span>
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
                    <div className="library-buttons">
                        <button className="button outline-light" onClick={onCreatePlaylist}>
                            <PlusIcon width={18} height={18}/>
                            Новый плейлист
                        </button>
                        <button className="button accent" disabled={uploader.isUploading} onClick={() => inputRef.current?.click()}>
                            <UploadIcon width={18} height={18}/>
                            {uploader.isUploading ? "Загружаем…" : "Загрузить музыку"}
                        </button>
                    </div>
                </div>

                <div className="section-header library-subheader">
                    <h2>Плейлисты</h2>
                    {isLoadingPlaylists && <span className="mono">обновляем из сервисов…</span>}
                </div>
                <div className="playlist-grid">
                    {playlists.map((playlist) => (
                        <button
                            key={playlist.id}
                            className={playlist.unavailable ? "playlist-card unavailable" : "playlist-card"}
                            onClick={() => onOpenPlaylist(playlist.id)}
                        >
                            <PlaylistCover key={playlist.id + (playlist.cover ?? "")} playlist={playlist} size="card"/>
                            <span className="playlist-card-title">{playlist.unavailable ? "[" + playlist.name.toUpperCase() + "]" : playlist.name}</span>
                            <span className="playlist-card-subtitle">{playlist.subtitle}</span>
                        </button>
                    ))}
                    {isLoadingPlaylists && !hasServicePlaylists && [0, 1].map((index) => (
                        <div key={"loading-" + index} className="playlist-card">
                            <span className="playlist-cover card loading">
                                <span className="playlist-loading"><NoteIcon/></span>
                            </span>
                            <span className="playlist-card-title muted">Плейлисты грузятся</span>
                            <span className="playlist-card-subtitle">Ждём ответа сервисов</span>
                        </div>
                    ))}
                    <button className="playlist-card" onClick={onCreatePlaylist}>
                        <span className="playlist-cover card playlist-new">
                            <PlusIcon width={44} height={44}/>
                        </span>
                        <span className="playlist-card-title">Новый плейлист</span>
                        <span className="playlist-card-subtitle">Соберите треки из любых сервисов</span>
                    </button>
                </div>

                <div className="section-header library-subheader">
                    <h2>Загрузки</h2>
                    <span className="mono">{trackCount(files.length)}</span>
                </div>

                {uploader.status && <p className="search-note">{uploader.status}</p>}
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
                                    title="Добавить в плейлист"
                                    onClick={(event) => {
                                        event.stopPropagation();
                                        openAddToPlaylist(trackFromFile(file));
                                    }}
                                >
                                    <PlusIcon width={18} height={18}/>
                                </button>
                                <LikeButton track={trackFromFile(file)}/>
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
            )}

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
