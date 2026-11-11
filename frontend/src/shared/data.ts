import coverOrange from "./images/covers/cover-orange.svg";
import coverOrbit from "./images/covers/cover-orbit.svg";
import coverForest from "./images/covers/cover-forest.svg";
import coverSun from "./images/covers/cover-sun.svg";
import type { Track } from "./types.ts";

export const tracks: Track[] = [
    { id: "1", title: "Радиовышка", artist: "Low Tower", cover: coverSun, duration: 238, sources: ["ЯМ", "SP", "SC"], source: "SC", edited: true, liked: true },
    { id: "2", title: "Солнцеворот", artist: "Орбита 9", cover: coverOrange, duration: 252, sources: ["SP", "YT"], source: "SP" },
    { id: "3", title: "Три орбиты", artist: "Станция Полночь", cover: coverOrbit, duration: 207, sources: ["ЯМ", "SP"], source: "ЯМ" },
    { id: "4", title: "Бег сквозь лес", artist: "Хвойный шум", cover: coverForest, duration: 400, sources: ["YT", "SC"], source: "SC" },
];
