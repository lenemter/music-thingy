import { useEffect, useRef } from "react";
import Cover from "../entities/Cover.tsx";
import Equalizer from "../entities/Equalizer.tsx";
import { formatTime, trackCount } from "../shared/format.ts";
import type { PlayerControls } from "../shared/player/usePlayer.ts";
import CloseIcon from "../shared/icons/close.svg?react";

type QueuePanelProps = {
    player: PlayerControls
    isClosing: boolean
    onClose: () => void
}

const VISIBLE_COUNT = 3;

function QueuePanel({ player, isClosing, onClose }: QueuePanelProps) {
    const panelRef = useRef<HTMLElement>(null);
    const current = player.queue[player.index];
    const items = player.queue.map((track, index) => ({ track, index }));
    // Показываем только ближайшее: 3 следующих и не больше 3 уже сыгранных
    const upcomingAll = items.slice(player.index + 1);
    const upcoming = upcomingAll.slice(0, VISIBLE_COUNT);
    const hiddenUpcoming = upcomingAll.length - upcoming.length;
    const played = items.slice(Math.max(0, player.index - VISIBLE_COUNT), player.index);

    useEffect(() => {
        function handleKey(event: KeyboardEvent) {
            if (event.key === "Escape") {
                onClose();
            }
        }
        function handlePointer(event: PointerEvent) {
            const target = event.target as Element;
            if (!panelRef.current?.contains(target) && !target.closest(".queue-toggle")) {
                onClose();
            }
        }
        document.addEventListener("keydown", handleKey);
        document.addEventListener("pointerdown", handlePointer);
        return () => {
            document.removeEventListener("keydown", handleKey);
            document.removeEventListener("pointerdown", handlePointer);
        };
    }, [onClose]);

    function renderRow(item: { track: typeof current, index: number }, isCurrent: boolean) {
        const { track, index } = item;
        return (
            <li key={track.id + ":" + index} className={isCurrent ? "queue-row current" : "queue-row"}>
                <button className="queue-row-main" onClick={() => player.playAt(index)} title={isCurrent ? "Пауза / продолжить" : "Включить"}>
                    {isCurrent && player.isPlaying ? <Equalizer/> : <span className="track-number">{index + 1 < 10 ? "0" + (index + 1) : index + 1}</span>}
                    <Cover src={track.cover} size="row"/>
                    <span className="track-info">
                        <span className="track-title">{track.title}</span>
                        <span className="track-artist">{track.artist}</span>
                    </span>
                    <span className="mono track-time">{formatTime(track.duration)}</span>
                </button>
                {!isCurrent && (
                    <button className="icon-button file-delete" title="Убрать из очереди" onClick={() => player.removeAt(index)}>
                        <CloseIcon width={14} height={14}/>
                    </button>
                )}
            </li>
        );
    }

    return (
        <aside ref={panelRef} className={isClosing ? "queue-panel closing" : "queue-panel"} aria-label="Очередь">
            <div className="queue-header">
                <div className="track-edit-heading">
                    <h2>Очередь</h2>
                    <span className="mono">{player.isEndless ? "волна" : trackCount(player.queue.length)}</span>
                </div>
                <button type="button" className="track-edit-close" title="Закрыть" aria-label="Закрыть" onClick={onClose}>
                    <CloseIcon width={18} height={18}/>
                </button>
            </div>

            <div className="queue-body">
                {current && (
                    <>
                        <span className="label">СЕЙЧАС ИГРАЕТ</span>
                        <ol className="track-list">{renderRow({ track: current, index: player.index }, true)}</ol>
                    </>
                )}

                <div className="queue-subheader">
                    <span className="label">ДАЛЕЕ</span>
                    {upcoming.length > 0 && (
                        <button className="link-plain section-link" onClick={player.clearUpcoming}>{player.isEndless ? "ОБНОВИТЬ" : "ОЧИСТИТЬ"}</button>
                    )}
                </div>
                {upcoming.length > 0 ? (
                    <>
                        <ol className="track-list">{upcoming.map((item) => renderRow(item, false))}</ol>
                        {hiddenUpcoming > 0 && <p className="search-note">и ещё {trackCount(hiddenUpcoming)}</p>}
                    </>
                ) : (
                    <p className="search-note">
                        {player.repeat === "one" ? "Текущий трек будет повторяться." : "Дальше ничего нет. Включите плейлист, волну или трек из поиска."}
                    </p>
                )}

                {played.length > 0 && (
                    <>
                        <span className="label">УЖЕ ИГРАЛИ</span>
                        <ol className="track-list queue-played">{played.map((item) => renderRow(item, false))}</ol>
                    </>
                )}
            </div>
        </aside>
    )
}

export default QueuePanel
