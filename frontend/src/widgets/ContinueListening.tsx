import PlaylistCover from "../entities/PlaylistCover.tsx";
import type { LibraryPlaylist } from "../shared/usePlaylists.ts";

type ContinueListeningProps = {
    playlists: LibraryPlaylist[]
    onOpenPlaylist: (id: string) => void
    onOpenLibrary: () => void
}

function ContinueListening({ playlists, onOpenPlaylist, onOpenLibrary }: ContinueListeningProps) {
    if (playlists.length === 0) {
        return null;
    }

    return (
        <section className="section">
            <div className="section-header">
                <h2>Продолжить слушать</h2>
                <button className="link-plain section-link" onClick={onOpenLibrary}>ВСЯ МЕДИАТЕКА →</button>
            </div>

            <div className="cards">
                {playlists.map((playlist) => (
                    <button
                        key={playlist.id}
                        className={playlist.unavailable ? "playlist-card unavailable" : "playlist-card"}
                        onClick={() => onOpenPlaylist(playlist.id)}
                    >
                        <PlaylistCover key={playlist.id + (playlist.cover ?? "")} playlist={playlist} size="card"/>
                        <span className="playlist-card-title">{playlist.name}</span>
                        <span className="playlist-card-subtitle">{playlist.subtitle}</span>
                    </button>
                ))}
            </div>
        </section>
    )
}

export default ContinueListening
