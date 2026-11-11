import Grain from "../entities/Grain.tsx";
import { formatLongTime, trackCount } from "../shared/format.ts";
import type { DailyWave } from "../shared/usePlaylists.ts";
import PlayIcon from "../shared/icons/play.svg?react";
import heroArt from "../shared/images/hero-art.svg";
import star from "../shared/images/star.svg";

type WaveOfDayProps = {
    wave: DailyWave
    onPlayWave: (seed: string) => void
}

// Вёрстка меняется по ширине самого блока (container queries в CSS):
// ≥ 1000 px — широкий вариант, 640–1000 — планшет, < 640 — телефон.
function WaveOfDay({ wave, onPlayWave }: WaveOfDayProps) {
    const isEmpty = wave.tracks.length === 0;
    const count = trackCount(wave.tracks.length).toUpperCase();
    const duration = formatLongTime(wave.duration > 0 ? Math.max(1, Math.round(wave.duration / 60)) : 0);


    return (
        <div className="hero-wrap">
            <section className="hero">
                <Grain/>
                <img className="hero-art" src={heroArt} alt=""/>

                <div className="hero-info">
                    <span className="hero-badge">ВОЛНА ДНЯ · {wave.date}</span>

                    <div className="hero-text">
                        <h1>{wave.title}</h1>
                        <p>{wave.description}</p>

                        {/* На телефоне счётчик — та же «таблетка», что на планшете, но в потоке над кнопками */}
                        <div className="hero-ticket hero-ticket-inline">
                            <span className="hero-ticket-icon"><img src={star} width="22" height="22" alt=""/></span>
                            <span className="hero-ticket-text">
                                <b>{count}</b>
                                <i>{duration}</i>
                            </span>
                        </div>

                        <div className="hero-buttons">
                            <button className="button dark hero-play" disabled={isEmpty} onClick={() => onPlayWave(wave.seed)}>
                                <PlayIcon width={18} height={18}/>
                                <span className="hero-play-long">Слушать волну</span>
                                <span className="hero-play-short">Слушать</span>
                            </button>
                        </div>
                    </div>
                </div>

                <div className="hero-ticket hero-ticket-corner">
                    <span className="hero-ticket-icon"><img src={star} width="22" height="22" alt=""/></span>
                    <span className="hero-ticket-text">
                        <b>{count}</b>
                        <i>{duration}</i>
                    </span>
                </div>

                <div className="hero-counter">
                    <span className="hero-counter-icon">
                        <img src={star} width="44" height="44" alt=""/>
                    </span>
                    <span className="hero-counter-big">{count}</span>
                    <span className="hero-counter-small">{duration}</span>
                </div>
            </section>
        </div>
    )
}

export default WaveOfDay
