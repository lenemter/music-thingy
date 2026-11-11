import Logo from "../entities/logo.tsx";
import Cover from "../entities/Cover.tsx";
import type { Playlist, Service } from "../shared/types.ts";
import HomeIcon from "../shared/icons/home.svg?react";
import SearchIcon from "../shared/icons/search.svg?react";
import LibraryIcon from "../shared/icons/library.svg?react";
import EditorIcon from "../shared/icons/editor.svg?react";
import SourcesIcon from "../shared/icons/sources.svg?react";
import PlusIcon from "../shared/icons/plus.svg?react";

type NavbarProps = {
    playlists: Playlist[]
    services: Service[]
    onOpenSources: () => void
    page: "home" | "library"
    onNavigate: (page: "home" | "library") => void
}

function Navbar({ playlists, services, onOpenSources, page, onNavigate }: NavbarProps) {
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
                <a className="nav-link" href="#"><SearchIcon/>Поиск</a>
                <a
                    className={page === "library" ? "nav-link active" : "nav-link"}
                    href="#"
                    onClick={(event) => { event.preventDefault(); onNavigate("library"); }}
                >
                    <LibraryIcon/>Медиатека
                </a>
                <a className="nav-link" href="#"><EditorIcon/>Редактор</a>
                <a className="nav-link" href="#" onClick={(event) => { event.preventDefault(); onOpenSources(); }}><SourcesIcon/>Источники</a>
            </div>

            <div className="nav-group">
                <div className="nav-title">
                    <span className="label">ПЛЕЙЛИСТЫ</span>
                    <button className="icon-button" title="Новый плейлист"><PlusIcon width={18} height={18}/></button>
                </div>

                {playlists.map((playlist) => (
                    <a key={playlist.id} className="nav-link" href="#">
                        <Cover src={playlist.cover} size="small"/>
                        {playlist.name}
                    </a>
                ))}
            </div>

            <a className="sources-card" href="#" onClick={(event) => { event.preventDefault(); onOpenSources(); }}>
                <span className="label">ИСТОЧНИКИ · {onlineCount} ИЗ {services.length}</span>
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
