import { useEffect, useState } from "react";
import Navbar from "./widgets/Navbar.tsx";
import MainPage from "./pages/MainPage.tsx";
import AuthPage from "./pages/AuthPage.tsx";
import Player from "./widgets/Player.tsx";
import SourcesModal from "./widgets/SourcesModal.tsx";
import { playlists, wave, albums, tracks } from "./shared/data.ts";
import type { Service, User, UserFile } from "./shared/types.ts";
import { fetchMe, fetchServices, fetchUploads, loadUser, logout, refreshTokens } from "./shared/api.ts";
import { defaultServices } from "./shared/music/services.ts";
import { usePlayer } from "./shared/player/usePlayer.ts";
import LibraryPage from "./pages/LibraryPage.tsx";
import { applyOverride } from "./shared/library.ts";
import { trackFromFile } from "./shared/music/convert.ts";

function App() {
    const [user, setUser] = useState<User | null>(loadUser());
    const player = usePlayer(tracks);
    const currentTrack = player.currentTrack ?? tracks[0];
    const [services, setServices] = useState<Service[]>(defaultServices);
    const [searchQuery, setSearchQuery] = useState("");
    const [isSourcesOpen, setIsSourcesOpen] = useState(false);
    const [files, setFiles] = useState<UserFile[]>([]);
    const [page, setPage] = useState<"home" | "library">("home");

    async function loadServiceStatuses() {
        try {
            setServices(await fetchServices());
        } catch {
            setServices(defaultServices);
        }
    }

    async function loadUploads() {
        try {
            const loaded = await fetchUploads();
            setFiles(loaded.map(applyOverride));
        } catch {
            setFiles([]);
        }
    }

    function handleFileDeleted(file: UserFile) {
        if (currentTrack.service === "local" && currentTrack.serviceId === String(file.id)) {
            player.stop();
        }
    }

    useEffect(() => {
        if (loadUser() === null) {
            return;
        }

        refreshTokens().then((isValid) => {
            if (!isValid) {
                logout();
                setUser(null);
                return;
            }
            fetchMe().then((me) => {
                if (me) {
                    setUser(me);
                }
            });
            loadServiceStatuses();
            loadUploads();
        });
    }, []);

    function handleLogin(newUser: User) {
        setUser(newUser);
        loadServiceStatuses();
        loadUploads();
    }

    function handleLogout() {
        player.stop();
        logout();
        setUser(null);
        setServices(defaultServices);
        setSearchQuery("");
        setFiles([]);
        setPage("home");
    }

    if (user === null) {
        return <AuthPage onLogin={handleLogin}/>
    }

    return (
      <div className={player.isPlaying ? "app is-playing" : "app"}>
          <div className="content">
              <Navbar
                  playlists={playlists}
                  services={services}
                  onOpenSources={() => setIsSourcesOpen(true)}
                  page={page}
                  onNavigate={(newPage) => {
                      setPage(newPage);
                      setSearchQuery("");
                  }}
              />
              {page === "library" && searchQuery === "" ? (
                  <LibraryPage
                      user={user}
                      services={services}
                      files={files}
                      playingFileId={currentTrack.service === "local" ? Number(currentTrack.serviceId) : null}
                      onFilesChange={setFiles}
                      onPlay={(file) => player.playTrack(trackFromFile(file), files.map(trackFromFile))}
                      onDeleted={handleFileDeleted}
                      onLogout={handleLogout}
                      onSearch={setSearchQuery}
                      onServicesChange={setServices}
                  />
              ) : (
              <MainPage
                  user={user}
                  services={services}
                  wave={wave}
                  albums={albums}
                  tracks={tracks}
                  files={files}
                  currentTrack={currentTrack}
                  onPlay={player.playTrack}
                  onLogout={handleLogout}
                  searchQuery={searchQuery}
                  onSearch={setSearchQuery}
                  onOpenSources={() => setIsSourcesOpen(true)}
                  onServicesChange={setServices}
                  onFilesChange={setFiles}
                  onFileDeleted={handleFileDeleted}
                  onOpenLibrary={() => setPage("library")}
              />
              )}
          </div>
          <Player key={currentTrack.id} track={currentTrack} player={player} services={services}/>

          {isSourcesOpen && (
              <SourcesModal
                  services={services}
                  onUpdate={setServices}
                  onClose={() => setIsSourcesOpen(false)}
              />
          )}
      </div>
    )
}

export default App
