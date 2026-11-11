import { useEffect, useState } from "react";
import TrackRow from "../entities/TrackRow.tsx";
import { searchMusic } from "../shared/api.ts";
import { trackFromRead } from "../shared/music/convert.ts";
import { getServiceName } from "../shared/music/services.ts";
import type { ServiceError } from "../shared/music/types.ts";
import type { Service, Track } from "../shared/types.ts";

type SearchResultsProps = {
    query: string
    currentTrack: Track
    services: Service[]
    onPlay: (track: Track, queue: Track[]) => void
    onClose: () => void
    onOpenSources: () => void
}

function SearchResults({ query, currentTrack, services, onPlay, onClose, onOpenSources }: SearchResultsProps) {
    const [tracks, setTracks] = useState<Track[]>([]);
    const [serviceErrors, setServiceErrors] = useState<ServiceError[]>([]);
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(true);

    const hasConnected = services.some((service) => service.online);

    useEffect(() => {
        let isActual = true;

        searchMusic({ query, types: ["track"], limit: 20 })
            .then((result) => {
                if (!isActual) {
                    return;
                }
                setTracks(result.tracks.map(trackFromRead));
                setServiceErrors(result.errors);
            })
            .catch((err) => {
                if (!isActual) {
                    return;
                }
                setTracks([]);
                setServiceErrors([]);
                setError(err instanceof Error ? err.message : "Не удалось выполнить поиск");
            })
            .finally(() => {
                if (isActual) {
                    setIsLoading(false);
                }
            });

        return () => {
            isActual = false;
        };
    }, [query]);

    return (
        <section className="section search-results">
            <div className="section-header">
                <h2>Поиск: «{query}»</h2>
                <button className="section-link search-close" onClick={onClose}>← НАЗАД</button>
            </div>

            {!hasConnected && (
                <p className="search-note">
                    Все сервисы выключены.{" "}
                    <button className="link-button" onClick={onOpenSources}>Включить источники</button>
                </p>
            )}

            {isLoading && <p className="search-note">Ищем во всех сервисах…</p>}

            {!isLoading && error && <p className="search-note error">{error}</p>}

            {!isLoading && !error && tracks.length === 0 && (
                <p className="search-note">Ничего не нашлось</p>
            )}

            {!isLoading && tracks.length > 0 && (
                <ol className="track-list">
                    {tracks.map((track, index) => (
                        <TrackRow
                            key={track.id}
                            track={track}
                            number={index + 1}
                            isPlaying={track.id === currentTrack.id}
                            services={services}
                            onPlay={(track) => onPlay(track, tracks)}
                        />
                    ))}
                </ol>
            )}

            {!isLoading && serviceErrors.map((item) => (
                <p key={item.service} className="search-note error">
                    {getServiceName(item.service)}: {item.message}
                </p>
            ))}
        </section>
    )
}

export default SearchResults
