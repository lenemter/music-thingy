import { useEffect, useRef, useState } from "react";
import type { Service, User } from "../shared/types.ts";
import SearchIcon from "../shared/icons/search.svg?react";
import BellIcon from "../shared/icons/bell.svg?react";
import LogoutIcon from "../shared/icons/logout.svg?react";

type HeaderProps = {
    user: User
    services: Service[]
    onLogout: () => void
}

function Header({ user, services, onLogout }: HeaderProps) {
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isClosing, setIsClosing] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);
    const closeTimer = useRef<number | undefined>(undefined);

    const onlineServices = services.filter((service) => service.online);
    const letter = user.name[0].toUpperCase();

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
            <form className="search" role="search">
                <SearchIcon/>
                <input type="search" placeholder="Трек, альбом или исполнитель — ищем во всех сервисах"/>
                <span className="tags">
                    {onlineServices.map((service) => (
                        <span key={service.code} className="tag" title={service.name}>{service.code}</span>
                    ))}
                </span>
            </form>
            <button className="icon-button big" title="Уведомления"><BellIcon/></button>

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
