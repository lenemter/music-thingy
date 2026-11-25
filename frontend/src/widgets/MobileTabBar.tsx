import type { ReactNode } from "react";

export type MobileTab = "home" | "library" | "sources"

type MobileTabBarProps = {
    active: MobileTab
    onSelect: (tab: MobileTab) => void
}

const TABS: { id: MobileTab, label: string, icon: ReactNode }[] = [
    {
        id: "home",
        label: "Главная",
        icon: <path d="M3 11l9-7 9 7v9h-6v-6H9v6H3z"/>,
    },
    {
        id: "library",
        label: "Медиатека",
        icon: <path d="M5 4v16M10 4v16M15 4l5 16"/>,
    },
    {
        id: "sources",
        label: "Источники",
        icon: <path d="M12 11v10M8 21l4-10 4 10M6.3 6.3a8 8 0 0 1 11.4 0M8.8 8.8a4.5 4.5 0 0 1 6.4 0"/>,
    },
];

function MobileTabBar({ active, onSelect }: MobileTabBarProps) {
    return (
        <nav className="mobile-tabs" aria-label="Разделы">
            {TABS.map((tab) => (
                <a
                    key={tab.id}
                    href="#"
                    aria-current={tab.id === active ? "page" : undefined}
                    onClick={(event) => {
                        event.preventDefault();
                        onSelect(tab.id);
                    }}
                >
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        {tab.icon}
                    </svg>
                    {tab.label}
                </a>
            ))}
        </nav>
    )
}

export default MobileTabBar
