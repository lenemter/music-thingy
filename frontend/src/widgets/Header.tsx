import type { Service, User } from "../shared/types.ts";
import SearchIcon from "../shared/icons/search.svg?react";
import BellIcon from "../shared/icons/bell.svg?react";

type HeaderProps = {
    user: User
    services: Service[]
}

function Header({ user, services }: HeaderProps) {
    const onlineServices = services.filter((service) => service.online);

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
            <button className="profile" title="Профиль">{user.name[0]}</button>
        </header>
    )
}

export default Header
