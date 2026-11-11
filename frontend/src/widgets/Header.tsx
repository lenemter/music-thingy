import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { Service, User } from "../shared/types.ts";
import type { ServiceId } from "../shared/music/types.ts";
import { setServiceActive } from "../shared/api.ts";
import SearchIcon from "../shared/icons/search.svg?react";
import CloseIcon from "../shared/icons/close.svg?react";
import LogoutIcon from "../shared/icons/logout.svg?react";

type HeaderProps = {
    user: User
    services: Service[]
    onLogout: () => void
    onSearch: (query: string) => void
    searchQuery?: string
    onServicesChange: (services: Service[]) => void
}

function Header({ user, services, onLogout, onSearch, onServicesChange, searchQuery = "" }: HeaderProps) {
    const [togglingService, setTogglingService] = useState<ServiceId | null>(null);
    const [unavailable, setUnavailable] = useState<ServiceId[]>([]);
    const [query, setQuery] = useState(searchQuery);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isClosing, setIsClosing] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);
    const closeTimer = useRef<number | undefined>(undefined);

    const letter = user.name[0].toUpperCase();
    const linkedServices = services.filter((service) => service.linked);

    async function toggleService(service: Service) {
        setTogglingService(service.id);
        try {
            const updated = await setServiceActive(service.id, !service.online);
            onServicesChange(updated);

            const result = updated.find((item) => item.id === service.id);
            if (!service.online && result && !result.online) {
                setUnavailable([...unavailable, service.id]);
            } else {
                setUnavailable(unavailable.filter((id) => id !== service.id));
            }
        } catch {
            setUnavailable(unavailable);
        }
        setTogglingService(null);
    }

    function getTagTitle(service: Service) {
        if (unavailable.includes(service.id)) {
            return service.name + " не настроен на сервере — привяжите аккаунт в «Источниках»";
        }
        return (service.online ? "Выключить " : "Включить ") + service.name;
    }

    function clearSearch() {
        setQuery("");
        onSearch("");
    }

    function handleSearch(event: FormEvent) {
        event.preventDefault();
        if (query.trim() !== "") {
            onSearch(query.trim());
        }
    }

    function openMenu() {
        clearTimeout(closeTimer.current);
        setIsClosing(false);
        setIsMenuOpen(true);
    }

    function closeMenu() {
        setIsClosing(true);
        clearTimeout(closeTimer.current);
        closeTimer.current = setTimeout(() => {
            setIsMenuOpen(false);
            setIsClosing(false);
        }, 200);
    }

    function toggleMenu() {
        if (isMenuOpen && !isClosing) {
            closeMenu();
        } else {
            openMenu();
        }
    }

    useEffect(() => {
        if (!isMenuOpen) {
            return;
        }

        function handleClick(event: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                closeMenu();
            }
        }

        function handleKey(event: KeyboardEvent) {
            if (event.key === "Escape") {
                closeMenu();
            }
        }

        document.addEventListener("mousedown", handleClick);
        document.addEventListener("keydown", handleKey);

        return () => {
            document.removeEventListener("mousedown", handleClick);
            document.removeEventListener("keydown", handleKey);
        };
    }, [isMenuOpen]);

    return (
        <header className="header">
            <form className="search" role="search" onSubmit={handleSearch}>
                <SearchIcon/>
                <input
                    type="search"
                    placeholder="Трек, альбом или исполнитель — ищем во всех сервисах"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                />
                {query !== "" && (
                    <button type="button" className="search-clear" title="Очистить" onClick={clearSearch}>
                        <CloseIcon/>
                    </button>
                )}
                <span className="tags">
                    {linkedServices.map((service) => (
                        <button
                            key={service.id}
                            type="button"
                            className={
                                "tag tag-button"
                                + (service.online ? " active" : "")
                                + (unavailable.includes(service.id) ? " unavailable" : "")
                            }
                            title={getTagTitle(service)}
                            disabled={togglingService !== null}
                            onClick={() => toggleService(service)}
                        >
                            {service.code}
                        </button>
                    ))}
                </span>
            </form>

            <div className="profile-menu" ref={menuRef}>
                <button className="profile" title="Профиль" onClick={toggleMenu}>
                    {letter}
                </button>

                {isMenuOpen && (
                    <div className={isClosing ? "profile-popup closing" : "profile-popup"}>
                        <div className="profile-info">
                            <span className="profile">{letter}</span>
                            <div className="profile-text">
                                <span className="profile-name">{user.name}</span>
                                <span className="profile-email">{user.email}</span>
                            </div>
                        </div>

                        <button className="button accent profile-logout" onClick={onLogout}>
                            <LogoutIcon/>
                            Выйти из аккаунта
                        </button>
                    </div>
                )}
            </div>
        </header>
    )
}

export default Header
