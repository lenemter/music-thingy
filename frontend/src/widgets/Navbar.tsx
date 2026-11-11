import Logo from "../entities/logo.tsx";
import PlaylistCover from "../entities/PlaylistCover.tsx";
import type { Service } from "../shared/types.ts";
import { showToast } from "../shared/toast.ts";
import type { LibraryPlaylist } from "../shared/usePlaylists.ts";
import HomeIcon from "../shared/icons/home.svg?react";
import LibraryIcon from "../shared/icons/library.svg?react";
import EditorIcon from "../shared/icons/editor.svg?react";
import PlusIcon from "../shared/icons/plus.svg?react";

type NavbarProps = {
    playlists: LibraryPlaylist[]
    activePlaylistId: string | null
    onOpenPlaylist: (id: string) => void
    onCreatePlaylist: () => void
    services: Service[]
    onOpenSources: () => void
    page: "home" | "library"
    onNavigate: (page: "home" | "library") => void
}

function Navbar({ playlists, activePlaylistId, onOpenPlaylist, onCreatePlaylist, services, onOpenSources, page, onNavigate }: NavbarProps) {
    const onlineCount = services.filter((service) => service.online).length;

    return (
        <nav className="navbar">
            <Logo/>

            <div className="nav-group">
                <a
                    className={page === "home" ? "nav-link active" : "nav-link"}
                    href="#"
                    onClick={(event) => { event.preventDefault(); onNavigate("home"); }}
                >
                    <HomeIcon/>Главная
                </a>
                <a
                    className={page === "library" && activePlaylistId === null ? "nav-link active" : "nav-link"}
                    href="#"
                    onClick={(event) => { event.preventDefault(); onNavigate("library"); }}
                >
                    <LibraryIcon/>Медиатека
                </a>
                <a className="nav-link" href="#" onClick={(event) => { event.preventDefault(); showToast("Раздел в разработке"); }}><EditorIcon/>Редактор</a>
            </div>

            <div className="nav-group nav-group-playlists">
                <div className="nav-title">
                    <span className="label">ПЛЕЙЛИСТЫ</span>
                    <button className="icon-button" title="Новый плейлист" onClick={onCreatePlaylist}><PlusIcon width={18} height={18}/></button>
                </div>

                <div className="nav-playlists">
                    {playlists.map((playlist) => (
                        <a
                            key={playlist.id}
                            className={["nav-link", playlist.id === activePlaylistId ? "active" : "", playlist.unavailable ? "unavailable" : ""].filter(Boolean).join(" ")}
                            href="#"
                            title={playlist.subtitle}
                            onClick={(event) => { event.preventDefault(); onOpenPlaylist(playlist.id); }}
                        >
                            <PlaylistCover key={playlist.id + (playlist.cover ?? "")} playlist={playlist} size="small"/>
                            <span className="nav-playlist-name">{playlist.name}</span>
                        </a>
                    ))}
                </div>
            </div>

            <a className="sources-card" href="#" onClick={(event) => { event.preventDefault(); onOpenSources(); }}>
                <span className="sources-card-head">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M12 11v10M8 21l4-10 4 10M6.3 6.3a8 8 0 0 1 11.4 0M8.8 8.8a4.5 4.5 0 0 1 6.4 0"/>
                    </svg>
                    <span className="sources-card-title">Источники</span>
                    <span className="sources-card-count">{onlineCount} ИЗ {services.length}</span>
                    <svg className="sources-card-arrow" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M9 6l6 6-6 6"/>
                    </svg>
                </span>
                <span className="sources-list">
                    {services.map((service) => (
                        <span key={service.id} className={service.online ? "source" : "source offline"}>
                            <span className="source-dot"/>
                            {service.shortName}
                        </span>
                    ))}
                </span>
            </a>
        </nav>
    )
}

export default Navbar
