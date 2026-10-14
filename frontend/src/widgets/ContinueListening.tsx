import Cover from "../entities/Cover.tsx";
import type { Album } from "../shared/types.ts";

type ContinueListeningProps = {
    albums: Album[]
}

function ContinueListening({ albums }: ContinueListeningProps) {
    return (
        <section className="section">
            <div className="section-header">
                <h2>Продолжить слушать</h2>
                <a className="section-link" href="#">ВСЯ ИСТОРИЯ →</a>
            </div>

            <div className="cards">
                {albums.map((album) => (
                    <a key={album.id} className="card" href="#">
                        <Cover src={album.cover} size="card"/>
                        <div>
                            <div className="card-title">{album.title}</div>
                            <div className="card-subtitle">{album.subtitle}</div>
                        </div>
                    </a>
                ))}
            </div>
        </section>
    )
}

export default ContinueListening
