import Header from "../widgets/Header.tsx";
import WaveOfDay from "../widgets/WaveOfDay.tsx";
import ContinueListening from "../widgets/ContinueListening.tsx";
import RecentTracks from "../widgets/RecentTracks.tsx";
import OwnMusic from "../widgets/OwnMusic.tsx";
import SearchResults from "../widgets/SearchResults.tsx";
import type { Service, Track, User, UserFile } from "../shared/types.ts";
import type { DailyWave, LibraryPlaylist } from "../shared/usePlaylists.ts";
import { trackFromFile } from "../shared/music/convert.ts";

type MainPageProps = {
    user: User
    services: Service[]
    wave: DailyWave
    recentTracks: Track[]
    continuePlaylists: LibraryPlaylist[]
    currentTrackId: string | null
    onOpenPlaylist: (id: string) => void
    onPlayWave: (seed: string) => void
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
    const { user, services, wave, recentTracks, continuePlaylists, currentTrackId, onOpenPlaylist, files, currentTrack, onPlay, onLogout } = props;
    const { searchQuery, onSearch, onOpenSources, onServicesChange, onFilesChange, onFileDeleted, onOpenLibrary } = props;
    const playingFileId = currentTrack.service === "local" ? Number(currentTrack.serviceId) : null;
    const enabledKey = services.filter((service) => service.online).map((service) => service.id).join(",");

    if (searchQuery !== "") {
        return (
            <main className="main">
                <Header key={searchQuery} user={user} services={services} searchQuery={searchQuery} onLogout={onLogout} onSearch={onSearch} onServicesChange={onServicesChange}/>
                <SearchResults
                    key={searchQuery + "|" + enabledKey}
                    query={searchQuery}
                    currentTrack={currentTrack}
                    services={services}
                    files={files}
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
            <WaveOfDay wave={wave} onPlayWave={props.onPlayWave}/>
            <ContinueListening playlists={continuePlaylists} onOpenPlaylist={onOpenPlaylist} onOpenLibrary={onOpenLibrary}/>

            <div className="bottom-row">
                <RecentTracks
                    tracks={recentTracks}
                    currentTrackId={currentTrackId}
                    services={services}
                    onPlay={onPlay}
                    onOpenSources={onOpenSources}
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
