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

function WaveOfDay({ wave, onPlayWave }: WaveOfDayProps) {
    const isEmpty = wave.tracks.length === 0;
    const count = trackCount(wave.tracks.length).toUpperCase();
    const duration = formatLongTime(wave.duration > 0 ? Math.max(1, Math.round(wave.duration / 60)) : 0);


    return (
        <div className="hero-wrap">
            <section className="hero">
                <svg className="hero-chain" viewBox="0 0 1500 520" preserveAspectRatio="xMaxYMid meet" aria-hidden="true">
                    <g fill="none" stroke="#F7C744" strokeWidth="2.5">
                        <circle cx="150" cy="260" r="190" opacity=".25"/>
                        <circle cx="390" cy="260" r="190" opacity=".4"/>
                        <circle cx="630" cy="260" r="190" opacity=".6"/>
                        <circle cx="870" cy="260" r="190" opacity=".8"/>
                        <circle cx="1110" cy="260" r="190"/>
                        <circle cx="1350" cy="260" r="190"/>
                    </g>
                    <path d="M1230 40C1238 200 1270 250 1450 260C1270 270 1238 320 1230 480C1222 320 1190 270 1010 260C1190 250 1222 200 1230 40Z" fill="#F2B51C"/>
                </svg>
                <Grain/>
                <img className="hero-art" src={heroArt} alt=""/>

                <div className="hero-info">
                    <span className="hero-badge">ВОЛНА ДНЯ · {wave.date}</span>

                    <div className="hero-text">
                        <h1>{wave.title}</h1>
                        <p>{wave.description}</p>

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
