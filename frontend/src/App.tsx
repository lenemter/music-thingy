import { useCallback, useEffect, useState } from "react";
import Navbar from "./widgets/Navbar.tsx";
import MainPage from "./pages/MainPage.tsx";
import AuthPage from "./pages/AuthPage.tsx";
import Player from "./widgets/Player.tsx";
import SourcesModal from "./widgets/SourcesModal.tsx";
import { tracks as demoTracks } from "./shared/data.ts";
import { addToHistory, getHistory } from "./shared/history.ts";
import { loadSession, saveSession } from "./shared/player/session.ts";
import { createWaveStream } from "./shared/waveStream.ts";
import type { Service, Track, User, UserFile } from "./shared/types.ts";
import { fetchMe, fetchServices, loadUser, logout, refreshTokens } from "./shared/api.ts";
import { defaultServices } from "./shared/music/services.ts";
import { usePlayer } from "./shared/player/usePlayer.ts";
import LibraryPage from "./pages/LibraryPage.tsx";
import { fetchUploads } from "./shared/library.ts";
import { trackFromFile } from "./shared/music/convert.ts";
import { usePlaylists } from "./shared/usePlaylists.ts";
import { homeRoute, parseHash, routeToHash } from "./shared/route.ts";
import type { Route } from "./shared/route.ts";
import type { LibraryPlaylist } from "./shared/usePlaylists.ts";
import { createPlaylist, deletePlaylist, renamePlaylist, subscribeAddToPlaylist } from "./shared/playlists.ts";
import PlaylistNameModal from "./widgets/PlaylistNameModal.tsx";
import AddToPlaylistModal from "./widgets/AddToPlaylistModal.tsx";
import ConfirmModal from "./widgets/ConfirmModal.tsx";
import Toast from "./widgets/Toast.tsx";
import QueuePanel from "./widgets/QueuePanel.tsx";
import { confirmAction } from "./shared/confirm.ts";
import { trackCount } from "./shared/format.ts";

type NameModal = { mode: "create", track?: Track } | { mode: "rename", playlist: LibraryPlaylist }

function App() {
    const [user, setUser] = useState<User | null>(loadUser());
    // После перезагрузки — та же очередь, что играла; если её нет, последние прослушанные треки
    const [initialSession] = useState(() => {
        const session = loadSession();
        if (session) {
            return session;
        }
        const recent = getHistory().slice(0, 10);
        return { queue: recent.length > 0 ? recent : demoTracks, index: 0, waveSeed: undefined };
    });
    const player = usePlayer(initialSession.queue, initialSession.index);
    const currentTrack = player.currentTrack ?? initialSession.queue[0];
    const [waveSeed, setWaveSeed] = useState<string | undefined>(initialSession.waveSeed);
    const [isWaveResumed, setIsWaveResumed] = useState(initialSession.waveSeed === undefined);
    const playingTrack = player.isPlaying ? player.currentTrack : undefined;

    useEffect(() => {
        if (playingTrack) {
            addToHistory(playingTrack);
        }
    }, [playingTrack]);
    const [services, setServices] = useState<Service[]>(defaultServices);
    const [route, setRoute] = useState<Route>(() => parseHash(window.location.hash));
    const { page, query: searchQuery, playlistId: openPlaylistId } = route;
    const [isSourcesOpen, setIsSourcesOpen] = useState(false);
    const [files, setFiles] = useState<UserFile[]>([]);
    const [servicesReady, setServicesReady] = useState(false);
    const { playlists, isLoading: isLoadingPlaylists, recentTracks, continuePlaylists, wave } = usePlaylists(user, services, files, servicesReady);

    const activeWaveSeed = player.isEndless ? waveSeed : isWaveResumed ? undefined : waveSeed;

    useEffect(() => {
        saveSession(player.queue, player.index, activeWaveSeed);
    }, [player.queue, player.index, activeWaveSeed]);

    // Восстановленная волна снова становится бесконечной, как только известны её треки
    const canResumeWave = !isWaveResumed && waveSeed !== undefined && wave.tracks.length > 1;
    useEffect(() => {
        if (!canResumeWave || !waveSeed) {
            return;
        }
        const stream = createWaveStream(wave.tracks, waveSeed + ":resume:" + Date.now(), player.queue);
        player.setExtend(stream.take);
        setIsWaveResumed(true);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [canResumeWave]);

    // Волна бесконечная: сначала текущий трек и 3 следующих, дальше плеер сам добирает треки из потока
    function playWave(seed: string) {
        const stream = createWaveStream(wave.tracks, seed);
        let first = stream.take(Math.min(4, wave.tracks.length));
        // Не начинаем с трека, который уже в плеере, — иначе кажется, что кнопка ничего не сделала
        if (first.length > 1 && player.currentTrack && first[0].id === player.currentTrack.id) {
            first = [...first.slice(1), ...stream.take(1)];
        }
        if (first.length === 0) {
            return;
        }
        setWaveSeed(seed);
        setIsWaveResumed(true);
        player.playTrack(first[0], first, stream.canRepeat ? stream.take : undefined);
    }

    const [nameModal, setNameModal] = useState<NameModal | null>(null);
    const [trackToAdd, setTrackToAdd] = useState<Track | null>(null);
    const [isQueueOpen, setIsQueueOpen] = useState(false);
    const closeQueue = useCallback(() => setIsQueueOpen(false), []);

    useEffect(() => subscribeAddToPlaylist(setTrackToAdd), []);

    function navigate(next: Route, replace = false) {
        setRoute(next);
        const hash = routeToHash(next);
        if (hash !== window.location.hash && !(hash === "#/" && window.location.hash === "")) {
            if (replace) {
                window.history.replaceState(null, "", hash);
            } else {
                window.history.pushState(null, "", hash);
            }
        }
    }

    useEffect(() => {
        function handlePop() {
            setRoute(parseHash(window.location.hash));
        }
        window.addEventListener("popstate", handlePop);
        return () => window.removeEventListener("popstate", handlePop);
    }, []);

    function openPlaylist(id: string | null) {
        navigate({ page: "library", playlistId: id, query: "" });
    }

    function setSearchQuery(query: string) {
        navigate({ ...route, query });
    }

    function handleNameSubmit(name: string) {
        const normalized = name.trim().toLocaleLowerCase("ru");
        const renamingId = nameModal?.mode === "rename" ? nameModal.playlist.id : null;
        const taken = playlists.find((playlist) =>
            playlist.kind !== "service"
            && playlist.id !== renamingId
            && playlist.name.trim().toLocaleLowerCase("ru") === normalized);
        if (taken) {
            throw new Error("Плейлист «" + taken.name + "» уже есть — придумайте другое название");
        }
        if (nameModal?.mode === "rename") {
            renamePlaylist(nameModal.playlist.id.slice("user:".length), name);
            return;
        }
        const created = createPlaylist(name, nameModal?.track);
        if (!nameModal?.track) {
            openPlaylist("user:" + created.id);
        }
    }

    async function handleDeletePlaylist(playlist: LibraryPlaylist) {
        const isConfirmed = await confirmAction({
            title: "Удалить плейлист «" + playlist.name + "»?",
            text: playlist.tracksCount > 0
                ? "В нём " + trackCount(playlist.tracksCount) + ". Удалится только список — сами треки и избранное не пострадают."
                : "Плейлист пустой — удалится только название.",
            confirmText: "Удалить",
            danger: true,
            icon: "delete",
        });
        if (!isConfirmed) {
            return;
        }
        deletePlaylist(playlist.id.slice("user:".length));
        navigate({ page: "library", playlistId: null, query: "" }, true);
    }

    async function loadServiceStatuses() {
        try {
            setServices(await fetchServices());
            setServicesReady(true);
        } catch {
            setServices(defaultServices);
        }
    }

    async function loadUploads() {
        try {
            setFiles(await fetchUploads());
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

    async function handleLogout() {
        const isConfirmed = await confirmAction({
            title: "Выйти из аккаунта?",
            text: "Плейлисты, лайки и загрузки останутся в этом браузере. Подключённые сервисы отключать не нужно.",
            confirmText: "Выйти",
            icon: "logout",
        });
        if (!isConfirmed) {
            return;
        }
        player.stop();
        logout();
        setUser(null);
        setServices(defaultServices);
        setFiles([]);
        navigate(homeRoute, true);
    }

    if (user === null) {
        return <AuthPage onLogin={handleLogin}/>
    }

    return (
      <div className={player.isPlaying ? "app is-playing" : "app"}>
          <div className="content">
              <Navbar
                  playlists={playlists}
                  activePlaylistId={page === "library" ? openPlaylistId : null}
                  onOpenPlaylist={openPlaylist}
                  onCreatePlaylist={() => setNameModal({ mode: "create" })}
                  services={services}
                  onOpenSources={() => setIsSourcesOpen(true)}
                  page={page}
                  onNavigate={(newPage) => {
                      navigate({ page: newPage, playlistId: null, query: "" });
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
                      playlists={playlists}
                      isLoadingPlaylists={isLoadingPlaylists}
                      openPlaylistId={openPlaylistId}
                      currentTrackId={player.currentTrack ? currentTrack.id : null}
                      onOpenPlaylist={openPlaylist}
                      onCreatePlaylist={() => setNameModal({ mode: "create" })}
                      onRenamePlaylist={(playlist) => setNameModal({ mode: "rename", playlist })}
                      onDeletePlaylist={handleDeletePlaylist}
                      onPlayTrack={player.playTrack}
                      onOpenSources={() => setIsSourcesOpen(true)}
                  />
              ) : (
              <MainPage
                  user={user}
                  services={services}
                  wave={wave}
                  recentTracks={recentTracks}
                  continuePlaylists={continuePlaylists}
                  onPlayWave={playWave}
                  currentTrackId={player.currentTrack ? currentTrack.id : null}
                  onOpenPlaylist={openPlaylist}
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
                  onOpenLibrary={() => navigate({ page: "library", playlistId: null, query: "" })}
              />
              )}
          </div>
          <Player
              key={currentTrack.id}
              track={currentTrack}
              player={player}
              services={services}
              isQueueOpen={isQueueOpen}
              onToggleQueue={() => setIsQueueOpen((value) => !value)}
          />
          {isQueueOpen && <QueuePanel player={player} onClose={closeQueue}/>}

          {isSourcesOpen && (
              <SourcesModal
                  services={services}
                  onUpdate={setServices}
                  onClose={() => setIsSourcesOpen(false)}
              />
          )}

          {trackToAdd && (
              <AddToPlaylistModal
                  track={trackToAdd}
                  playlists={playlists}
                  onCreateNew={(track) => setNameModal({ mode: "create", track })}
                  onClose={() => setTrackToAdd(null)}
              />
          )}

          <ConfirmModal/>
          <Toast/>

          {nameModal && (
              <PlaylistNameModal
                  title={nameModal.mode === "rename" ? "Переименовать плейлист" : "Новый плейлист"}
                  submitText={nameModal.mode === "rename" ? "Сохранить" : "Создать"}
                  initialName={nameModal.mode === "rename" ? nameModal.playlist.name : ""}
                  note={nameModal.mode === "create" && nameModal.track ? "Трек «" + nameModal.track.title + "» сразу попадёт в новый плейлист." : undefined}
                  onSubmit={handleNameSubmit}
                  onClose={() => setNameModal(null)}
                  onCancel={() => {
                      const returnTrack = nameModal.mode === "create" ? nameModal.track : undefined;
                      setNameModal(null);
                      if (returnTrack) {
                          setTrackToAdd(returnTrack);
                      }
                  }}
              />
          )}
      </div>
    )
}

export default App
