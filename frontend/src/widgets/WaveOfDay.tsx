import Grain from "../entities/Grain.tsx";
import { formatLongTime } from "../shared/format.ts";
import type { Wave } from "../shared/types.ts";
import PlayIcon from "../shared/icons/play.svg?react";
import ShuffleIcon from "../shared/icons/shuffle.svg?react";
import heroArt from "../shared/images/hero-art.svg";
import star from "../shared/images/star.svg";

type WaveOfDayProps = {
    wave: Wave
}

function WaveOfDay({ wave }: WaveOfDayProps) {
    return (
        <section className="hero">
            <Grain/>

            <div className="hero-info">
                <span className="hero-badge">ВОЛНА ДНЯ · {wave.date}</span>
                <div className="hero-text">
                    <h1>{wave.title}</h1>
                    <p>{wave.description}</p>
                    <div className="hero-buttons">
                        <button className="button dark"><PlayIcon width={18} height={18}/>Слушать волну</button>
                        <button className="button outline"><ShuffleIcon width={18} height={18}/>Перемешать</button>
                    </div>
                </div>
            </div>

            <img className="hero-art" src={heroArt} alt=""/>

            <div className="hero-counter">
                <span className="hero-counter-icon">
                    <img src={star} width="44" height="44" alt=""/>
                </span>
                <span className="hero-counter-big">{wave.trackCount} ТРЕКОВ</span>
                <span className="hero-counter-small">{formatLongTime(wave.duration)}</span>
            </div>
        </section>
    )
}

export default WaveOfDay
