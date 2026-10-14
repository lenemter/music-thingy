import coverSky from "./images/covers/cover-sky.svg";
import coverOrange from "./images/covers/cover-orange.svg";
import coverOrbit from "./images/covers/cover-orbit.svg";
import coverForest from "./images/covers/cover-forest.svg";
import coverSun from "./images/covers/cover-sun.svg";
import type { Service, Track, Album, Playlist, UserFile, Wave, User } from "./types.ts";

export const user: User = {
    name: "Тест",
};

export const services: Service[] = [
    { code: "ЯМ", name: "Яндекс Музыка", shortName: "Яндекс", online: true },
    { code: "SP", name: "Spotify", shortName: "Spotify", online: true },
    { code: "SC", name: "SoundCloud", shortName: "SoundCloud", online: false },
    { code: "YT", name: "YouTube", shortName: "YouTube", online: false },
];

export const playlists: Playlist[] = [
    { id: 1, name: "Ночные поездки", cover: coverSky },
    { id: 2, name: "Фокус · без слов", cover: coverForest },
    { id: 3, name: "Лето 2026", cover: coverOrange },
    { id: 4, name: "Мои загрузки", cover: coverOrbit },
];

export const wave: Wave = {
    date: "11.10",
    title: "Эфир на закате",
    description: "38 треков из Яндекс Музыки, Spotify и SoundCloud, собранных по вашим прослушиваниям за неделю. Один поток — без переключения приложений.",
    trackCount: 36245,
    duration: 4389432,
};

export const albums: Album[] = [
    { id: 1, title: "Ночные поездки", subtitle: "Плейлист · 64 трека", cover: coverSky },
    { id: 2, title: "Солнцеворот", subtitle: "Орбита 9 · альбом", cover: coverOrange },
    { id: 3, title: "Три орбиты", subtitle: "Станция Полночь · EP", cover: coverOrbit },
    { id: 4, title: "Бег сквозь лес", subtitle: "Хвойный шум · альбом", cover: coverForest },
    { id: 5, title: "Сигнал 404", subtitle: "Low Tower · альбом", cover: coverSun },
];

export const tracks: Track[] = [
    { id: 1, title: "Радиовышка", artist: "Low Tower", cover: coverSun, duration: 238, sources: ["ЯМ", "SP", "SC"], source: "SC", edited: true, liked: true },
    { id: 2, title: "Солнцеворот", artist: "Орбита 9", cover: coverOrange, duration: 252, sources: ["SP", "YT"], source: "SP" },
    { id: 3, title: "Три орбиты", artist: "Станция Полночь", cover: coverOrbit, duration: 207, sources: ["ЯМ", "SP"], source: "ЯМ" },
    { id: 4, title: "Бег сквозь лес", artist: "Хвойный шум", cover: coverForest, duration: 400, sources: ["YT", "SC"], source: "SC" },
];

export const files: UserFile[] = [
    { id: 1, name: "демо_гараж_v3", type: "WAV", duration: 171, size: 31 },
    { id: 2, name: "Ночной эфир (рип с кассеты)", type: "MP3", duration: 276, size: 9 },
];
