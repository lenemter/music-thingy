import TrackRow from "../entities/TrackRow.tsx";
import type { Service, Track } from "../shared/types.ts";

type RecentTracksProps = {
    tracks: Track[]
    currentTrackId: string | null
    services: Service[]
    onPlay: (track: Track, queue: Track[]) => void
    onOpenSources: () => void
}

function RecentTracks({ tracks, currentTrackId, services, onPlay, onOpenSources }: RecentTracksProps) {
    const playable = tracks.filter((track) => !track.unavailable);

    return (
        <section className="section recommendations">
            <div className="section-header">
                <h2>Недавние</h2>
            </div>

            {tracks.length === 0 ? (
                <div className="library-empty">
                    <p>Вы ещё ничего не слушали. Найдите трек через поиск сверху или включите свою музыку — последние 10 треков будут здесь.</p>
                </div>
            ) : (
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
                        />
                    ))}
                </ol>
            )}
        </section>
    )
}

export default RecentTracks
