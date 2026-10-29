import { useEffect, useState } from "react";
import Navbar from "./widgets/Navbar.tsx";
import MainPage from "./pages/MainPage.tsx";
import AuthPage from "./pages/AuthPage.tsx";
import Player from "./widgets/Player.tsx";
import { services, playlists, wave, albums, tracks, files } from "./shared/data.ts";
import type { User } from "./shared/types.ts";
import { loadUser, logout, refreshTokens } from "./shared/api.ts";

function App() {
    const [user, setUser] = useState<User | null>(loadUser());
    const [currentTrack, setCurrentTrack] = useState(tracks[0]);
    const [currentTime] = useState(102);

    useEffect(() => {
        if (loadUser() === null) {
            return;
        }

        refreshTokens().then((isValid) => {
            if (!isValid) {
                logout();
                setUser(null);
            }
        });
    }, []);

    function handleLogout() {
        logout();
        setUser(null);
    }

    if (user === null) {
        return <AuthPage onLogin={setUser}/>
    }

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
                  onLogout={handleLogout}
              />
          </div>
          <Player key={currentTrack.id} track={currentTrack} currentTime={currentTime} services={services}/>
      </div>
    )
}

export default App
