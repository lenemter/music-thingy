import { useEffect, useState } from "react";
import TrackRow from "../entities/TrackRow.tsx";
import PlaylistCover from "../entities/PlaylistCover.tsx";
import { fetchServicePlaylist } from "../shared/api.ts";
import { trackFromRead } from "../shared/music/convert.ts";
import { removeTrackFromPlaylist } from "../shared/playlists.ts";
import { markPlaylistPlayed } from "../shared/history.ts";
import { getTrackKey } from "../shared/favorites.ts";
import { formatLongTime, trackCount } from "../shared/format.ts";
import type { LibraryPlaylist } from "../shared/usePlaylists.ts";
import type { Service, Track } from "../shared/types.ts";
import PlayIcon from "../shared/icons/play.svg?react";

type PlaylistViewProps = {
    playlist: LibraryPlaylist
    services: Service[]
    currentTrackId: string | null
    onPlay: (track: Track, queue: Track[]) => void
    onBack: () => void
    onRename: () => void
    onDelete: () => void
    onOpenSources: () => void
}

const kindLabels = {
    liked: "СОБИРАЕТСЯ САМ",
    user: "ВАШ ПЛЕЙЛИСТ",
    service: "ИЗ СЕРВИСА",
};

// Треки, с которых сняли лайк, остаются на своих местах, пока пользователь не выйдет из плейлиста.
function keepRemoved(shown: Track[], current: Track[]) {
    const currentByKey = new Map(current.map((track) => [getTrackKey(track), track]));
    const shownKeys = new Set(shown.map(getTrackKey));
    const added = current.filter((track) => !shownKeys.has(getTrackKey(track)));
    const kept = shown.map((track) => currentByKey.get(getTrackKey(track)) ?? { ...track, liked: false });
    return [...added, ...kept];
}

function PlaylistView(props: PlaylistViewProps) {
    const { playlist, services, currentTrackId, onBack, onRename, onDelete, onOpenSources } = props;

    function onPlay(track: Track, queue: Track[]) {
        markPlaylistPlayed(playlist.id);
        props.onPlay(track, queue);
    }
    const [loadedTracks, setLoadedTracks] = useState<Track[] | null>(null);
    const needsLoading = playlist.tracks === null && !playlist.unavailable;
    // Компонент пересоздаётся для каждого плейлиста (key), поэтому начальное состояние задаём сразу.
    const [isLoading, setIsLoading] = useState(needsLoading);
    const [error, setError] = useState("");
    const [likedShown, setLikedShown] = useState<Track[]>(playlist.tracks ?? []);
    const [likedSource, setLikedSource] = useState(playlist.tracks);

    useEffect(() => {
        if (!needsLoading || !playlist.service || !playlist.serviceId) {
            return;
        }
        let isCancelled = false;
        fetchServicePlaylist(playlist.service, playlist.serviceId)
            .then((data) => {
                if (!isCancelled) {
                    setLoadedTracks((data.tracks ?? []).map(trackFromRead));
                }
            })
            .catch((err) => {
                if (!isCancelled) {
                    setError(err instanceof Error ? err.message : "Не удалось загрузить плейлист");
                }
            })
            .finally(() => {
                if (!isCancelled) {
                    setIsLoading(false);
                }
            });
        return () => {
            isCancelled = true;
        };
    }, [needsLoading, playlist.service, playlist.serviceId]);

    if (playlist.kind === "liked" && playlist.tracks !== likedSource) {
        setLikedSource(playlist.tracks);
        setLikedShown(keepRemoved(likedShown, playlist.tracks ?? []));
    }

    const tracks = playlist.kind === "liked" ? likedShown : (playlist.tracks ?? loadedTracks ?? []);
    const playable = tracks.filter((track) => !track.unavailable);
    const unavailableCount = tracks.length - playable.length;
    const duration = tracks.reduce((total, track) => total + (track.duration || 0), 0);
    const meta = [trackCount(playlist.tracks ? tracks.length : (loadedTracks?.length ?? playlist.tracksCount))];
    if (duration > 0) {
        meta.push(formatLongTime(Math.round(duration / 60)));
    }
    if (unavailableCount > 0) {
        meta.push(unavailableCount + " недоступно");
    }

    return (
        <section className="section library">
            <button className="link-plain section-link playlist-back" onClick={onBack}>← МЕДИАТЕКА</button>

            <div className="playlist-hero">
                <div className="playlist-hero-cover">
                    <PlaylistCover key={playlist.id} playlist={playlist} size="card"/>
                </div>
                <div className="playlist-hero-info">
                    <span className="label">ПЛЕЙЛИСТ · {kindLabels[playlist.kind]}</span>
                    <h1 className="library-title">{playlist.name}</h1>
                    <span className="mono">{playlist.unavailable ? playlist.subtitle : meta.join(" · ")}</span>
                    <div className="playlist-actions">
                        {playlist.unavailable ? (
                            <button className="button accent" onClick={onOpenSources}>Подключить {playlist.unavailable}</button>
                        ) : (
                            <button className="button accent" disabled={playable.length === 0} onClick={() => onPlay(playable[0], playable)}>
                                <PlayIcon width={18} height={18}/>
                                Слушать
                            </button>
                        )}
                        {playlist.kind === "user" && (
                            <>
                                <button className="button outline-light small" onClick={onRename}>Переименовать</button>
                                <button className="button outline-light small" onClick={onDelete}>Удалить</button>
                            </>
                        )}
                        {playlist.externalUrl && (
                            <a className="button outline-light small" href={playlist.externalUrl} target="_blank" rel="noopener noreferrer">
                                Открыть в сервисе
                            </a>
                        )}
                    </div>
                </div>
            </div>

            {isLoading && <p className="search-note">Загружаем треки…</p>}
            {error && <p className="auth-error">{error}</p>}

            {!isLoading && !error && !playlist.unavailable && tracks.length === 0 && (
                <div className="library-empty">
                    <p>
                        {playlist.kind === "liked" && "Ставьте сердечко трекам — они будут собираться здесь. Лайки из подключённых сервисов тоже появятся тут."}
                        {playlist.kind === "user" && "Плейлист пуст. Нажмите «+» у любого трека в поиске, рекомендациях или медиатеке, чтобы добавить его сюда."}
                        {playlist.kind === "service" && "В этом плейлисте нет треков, которые можно показать."}
                    </p>
                </div>
            )}

            {tracks.length > 0 && (
                <ol className="track-list">
                    {tracks.map((track, index) => (
                        <TrackRow
                            key={track.id}
                            track={track}
                            number={index + 1}
                            isPlaying={track.id === currentTrackId}
                            services={services}
                            onPlay={(item) => onPlay(item, playable)}
                            onUnavailableClick={onOpenSources}
                            onRemove={playlist.kind === "user"
                                ? (item) => removeTrackFromPlaylist(playlist.id.slice("user:".length), item)
                                : undefined}
                        />
                    ))}
                </ol>
            )}
        </section>
    )
}

export default PlaylistView
