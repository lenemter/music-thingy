import Header from "../widgets/Header.tsx";
import WaveOfDay from "../widgets/WaveOfDay.tsx";
import ContinueListening from "../widgets/ContinueListening.tsx";
import Recommendations from "../widgets/Recommendations.tsx";
import OwnMusic from "../widgets/OwnMusic.tsx";
import SearchResults from "../widgets/SearchResults.tsx";
import type { Album, Service, Track, User, UserFile, Wave } from "../shared/types.ts";
import { trackFromFile } from "../shared/music/convert.ts";

type MainPageProps = {
    user: User
    services: Service[]
    wave: Wave
    albums: Album[]
    tracks: Track[]
    files: UserFile[]
    currentTrack: Track
    onPlay: (track: Track, queue: Track[]) => void
    onLogout: () => void
    searchQuery: string
    onSearch: (query: string) => void
    onOpenSources: () => void
    onServicesChange: (services: Service[]) => void
    onFilesChange: (files: UserFile[]) => void
    onFileDeleted: (file: UserFile) => void
    onOpenLibrary: () => void
}

function MainPage(props: MainPageProps) {
    const { user, services, wave, albums, tracks, files, currentTrack, onPlay, onLogout } = props;
    const { searchQuery, onSearch, onOpenSources, onServicesChange, onFilesChange, onFileDeleted, onOpenLibrary } = props;
    const playingFileId = currentTrack.service === "local" ? Number(currentTrack.serviceId) : null;
    const enabledKey = services.filter((service) => service.online).map((service) => service.id).join(",");

    if (searchQuery !== "") {
        return (
            <main className="main">
                <Header user={user} services={services} onLogout={onLogout} onSearch={onSearch} onServicesChange={onServicesChange}/>
                <SearchResults
                    key={searchQuery + "|" + enabledKey}
                    query={searchQuery}
                    currentTrack={currentTrack}
                    services={services}
                    onPlay={onPlay}
                    onClose={() => onSearch("")}
                    onOpenSources={onOpenSources}
                />
            </main>
        )
    }

    return (
        <main className="main">
            <Header user={user} services={services} onLogout={onLogout} onSearch={onSearch} onServicesChange={onServicesChange}/>
            <WaveOfDay wave={wave}/>
            <ContinueListening albums={albums}/>

            <div className="bottom-row">
                <Recommendations
                    tracks={tracks}
                    currentTrack={currentTrack}
                    services={services}
                    onPlay={onPlay}
                />
                <OwnMusic
                    files={files}
                    playingFileId={playingFileId}
                    onFilesChange={onFilesChange}
                    onPlay={(file) => onPlay(trackFromFile(file), files.map(trackFromFile))}
                    onDeleted={onFileDeleted}
                    onOpenLibrary={onOpenLibrary}
                />
            </div>
        </main>
    )
}

export default MainPage
