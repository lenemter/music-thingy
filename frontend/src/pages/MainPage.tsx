import Header from "../widgets/Header.tsx";
import WaveOfDay from "../widgets/WaveOfDay.tsx";
import ContinueListening from "../widgets/ContinueListening.tsx";
import Recommendations from "../widgets/Recommendations.tsx";
import OwnMusic from "../widgets/OwnMusic.tsx";
import type { Album, Service, Track, User, UserFile, Wave } from "../shared/types.ts";

type MainPageProps = {
    user: User
    services: Service[]
    wave: Wave
    albums: Album[]
    tracks: Track[]
    files: UserFile[]
    currentTrack: Track
    onPlay: (track: Track) => void
    onLogout: () => void
}

function MainPage({ user, services, wave, albums, tracks, files, currentTrack, onPlay, onLogout }: MainPageProps) {
    return (
        <main className="main">
            <Header user={user} services={services} onLogout={onLogout}/>
            <WaveOfDay wave={wave}/>
            <ContinueListening albums={albums}/>

            <div className="bottom-row">
                <Recommendations
                    tracks={tracks}
                    currentTrack={currentTrack}
                    services={services}
                    onPlay={onPlay}
                />
                <OwnMusic files={files}/>
            </div>
        </main>
    )
}

export default MainPage
