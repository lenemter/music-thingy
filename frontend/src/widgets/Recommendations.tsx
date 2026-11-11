import TrackRow from "../entities/TrackRow.tsx";
import type { Service, Track } from "../shared/types.ts";

type RecommendationsProps = {
    tracks: Track[]
    currentTrack: Track
    services: Service[]
    onPlay: (track: Track, queue: Track[]) => void
}

function Recommendations({ tracks, currentTrack, services, onPlay }: RecommendationsProps) {
    return (
        <section className="section recommendations">
            <div className="section-header">
                <h2>Рекомендации для вас</h2>
                <span className="mono">по истории из всех сервисов</span>
            </div>

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
        </section>
    )
}

export default Recommendations
