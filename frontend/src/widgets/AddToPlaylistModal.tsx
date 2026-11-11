import { useEffect, useState } from "react";
import PlaylistCover from "../entities/PlaylistCover.tsx";
import { addTrackToPlaylist, getUserPlaylists, hasTrack, removeTrackFromPlaylist } from "../shared/playlists.ts";
import type { LibraryPlaylist } from "../shared/usePlaylists.ts";
import type { Track } from "../shared/types.ts";
import CloseIcon from "../shared/icons/close.svg?react";
import PlusIcon from "../shared/icons/plus.svg?react";

type AddToPlaylistModalProps = {
    track: Track
    playlists: LibraryPlaylist[]
    onCreateNew: (track: Track) => void
    onClose: () => void
}

function AddToPlaylistModal({ track, playlists, onCreateNew, onClose }: AddToPlaylistModalProps) {
    const [isClosing, setIsClosing] = useState(false);
    const [error, setError] = useState("");
    const own = playlists.filter((playlist) => playlist.kind === "user");
    const stored = getUserPlaylists();

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

    function addTo(playlistId: string) {
        try {
            addTrackToPlaylist(playlistId, track);
            closeModal();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Не удалось добавить");
        }
    }

    function removeFrom(playlistId: string) {
        setError("");
        try {
            removeTrackFromPlaylist(playlistId, track);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Не удалось убрать");
        }
    }

    return (
        <div className={isClosing ? "modal-overlay closing" : "modal-overlay"} onMouseDown={closeModal}>
            <div className="modal playlist-modal" onMouseDown={(event) => event.stopPropagation()}>
                <div className="track-edit-header">
                    <div className="track-edit-heading">
                        <h2>В плейлист</h2>
                        <span className="mono">{track.title} — {track.artist}</span>
                    </div>
                    <button type="button" className="track-edit-close" title="Закрыть" onClick={closeModal}>
                        <CloseIcon width={20} height={20}/>
                    </button>
                </div>

                <ul className="playlist-pick">
                    <li>
                        <button className="playlist-pick-item" onClick={() => { onCreateNew(track); closeModal(); }}>
                            <span className="playlist-pick-new"><PlusIcon width={16} height={16}/></span>
                            <span className="track-title">Новый плейлист</span>
                        </button>
                    </li>
                    {own.map((playlist) => {
                        const id = playlist.id.slice("user:".length);
                        const storedPlaylist = stored.find((item) => item.id === id);
                        const isAdded = storedPlaylist ? hasTrack(storedPlaylist, track) : false;
                        return (
                            <li key={playlist.id} className="playlist-pick-row">
                                <button className="playlist-pick-item" disabled={isAdded} onClick={() => addTo(id)}>
                                    <PlaylistCover key={playlist.id} playlist={playlist} size="small"/>
                                    <span className="track-info">
                                        <span className="track-title">{playlist.name}</span>
                                        <span className="track-artist">{playlist.subtitle}</span>
                                    </span>
                                </button>
                                {isAdded && (
                                    <button
                                        type="button"
                                        className="playlist-pick-remove"
                                        title={"Убрать трек из «" + playlist.name + "»"}
                                        onClick={() => removeFrom(id)}
                                    >
                                        <CloseIcon width={14} height={14}/>
                                        УБРАТЬ
                                    </button>
                                )}
                            </li>
                        );
                    })}
                </ul>

                {own.length === 0 && <p className="modal-text">Своих плейлистов пока нет — создайте первый.</p>}
                {error && <p className="auth-error">{error}</p>}
            </div>
        </div>
    )
}

export default AddToPlaylistModal
