import { useState } from "react";
import Navbar from "./widgets/Navbar.tsx";
import MainPage from "./pages/MainPage.tsx";
import Player from "./widgets/Player.tsx";
import { user, services, playlists, wave, albums, tracks, files } from "./shared/data.ts";

function App() {
    const [currentTrack, setCurrentTrack] = useState(tracks[0]);
    const [currentTime] = useState(102);

    return (
      <div className="app">
          <div className="content">
              <Navbar playlists={playlists} services={services}/>
              <MainPage
                  user={user}
                  services={services}
                  wave={wave}
                  albums={albums}
                  tracks={tracks}
                  files={files}
                  currentTrack={currentTrack}
                  onPlay={setCurrentTrack}
              />
          </div>
          <Player key={currentTrack.id} track={currentTrack} currentTime={currentTime} services={services}/>
      </div>
    )
}

export default App
