import coverAtom from "./images/covers/cover-atom.svg";
import coverBarcode from "./images/covers/cover-barcode.svg";
import coverFlash from "./images/covers/cover-flash.svg";
import coverForest from "./images/covers/cover-forest.svg";
import coverGlobe from "./images/covers/cover-globe.svg";
import coverGradient from "./images/covers/cover-gradient.svg";
import coverIntersection from "./images/covers/cover-intersection.svg";
import coverLevel from "./images/covers/cover-level.svg";
import coverOrange from "./images/covers/cover-orange.svg";
import coverOrbit from "./images/covers/cover-orbit.svg";
import coverRings from "./images/covers/cover-rings.svg";
import coverSky from "./images/covers/cover-sky.svg";
import coverSun from "./images/covers/cover-sun.svg";
import coverSunset from "./images/covers/cover-sunset.svg";

export const coverTemplates = [
    coverAtom,
    coverBarcode,
    coverFlash,
    coverForest,
    coverGlobe,
    coverGradient,
    coverIntersection,
    coverLevel,
    coverOrange,
    coverOrbit,
    coverRings,
    coverSky,
    coverSun,
    coverSunset,
];

const TEMPLATE_PREFIX = "template:";

export function randomTemplate() {
    return Math.floor(Math.random() * coverTemplates.length);
}

export function templateKey(index: number) {
    return TEMPLATE_PREFIX + index;
}

export function coverUrl(cover: string | null | undefined) {
    if (cover && cover.startsWith(TEMPLATE_PREFIX)) {
        const index = Number(cover.slice(TEMPLATE_PREFIX.length));
        return coverTemplates[index] ?? coverTemplates[0];
    }
    return cover || undefined;
}

export function fallbackCover(id: number | string) {
    let sum = 0;
    const text = String(id);
    for (let i = 0; i < text.length; i++) {
        sum += text.charCodeAt(i);
    }
    return coverTemplates[sum % coverTemplates.length];
}

export function templateImage(index: number): Promise<Blob> {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            const canvas = document.createElement("canvas");
            canvas.width = 320;
            canvas.height = 320;
            canvas.getContext("2d")?.drawImage(img, 0, 0, 320, 320);
            canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("Не удалось подготовить обложку"))), "image/jpeg", 0.9);
        };
        img.onerror = () => reject(new Error("Не удалось открыть обложку"));
        img.src = coverTemplates[index];
    });
}
