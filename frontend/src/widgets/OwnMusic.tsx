import { formatTime } from "../shared/format.ts";
import type { UserFile } from "../shared/types.ts";
import UploadIcon from "../shared/icons/upload.svg?react";
import sunStar from "../shared/images/sun-star.svg";

type OwnMusicProps = {
    files: UserFile[]
}

function OwnMusic({ files }: OwnMusicProps) {
    return (
        <section className="section own-music">
            <img className="own-music-star" src={sunStar} alt=""/>

            <h2>Своя музыка</h2>
            <p>
                Загрузите MP3, FLAC или WAV — треки встанут рядом с музыкой из сервисов.
                Их можно обрезать и обработать в редакторе.
            </p>
            <a className="button accent" href="#"><UploadIcon width={18} height={18}/>Загрузить файлы</a>

            <ul className="files">
                {files.map((file) => (
                    <li key={file.id} className="file">
                        <span className="file-type">{file.type}</span>
                        <span className="file-info">
                            <span className="file-name">{file.name}</span>
                            <span className="mono">{formatTime(file.duration)} · {file.size} МБ</span>
                        </span>
                        <a className="file-edit" href="#">ПРАВИТЬ</a>
                    </li>
                ))}
            </ul>
        </section>
    )
}

export default OwnMusic
