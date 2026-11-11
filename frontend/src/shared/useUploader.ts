import { useState } from "react";
import { uploadAudioFile } from "./api.ts";
import { readAudioTags } from "./audioTags.ts";
import type { AudioTags } from "./audioTags.ts";
import { saveTrackInfo } from "./library.ts";
import { randomTemplate } from "./coverTemplates.ts";
import type { TrackInfo } from "./library.ts";
import type { UserFile } from "./types.ts";

export const AUDIO_ACCEPT = ".mp3,.wav,.flac,.ogg,.m4a,.aac,audio/*";

export function useUploader(files: UserFile[], onFilesChange: (files: UserFile[]) => void) {
    const [status, setStatus] = useState("");
    const [errors, setErrors] = useState<string[]>([]);
    const [isUploading, setIsUploading] = useState(false);

    async function uploadFiles(list: File[]) {
        if (list.length === 0 || isUploading) {
            return;
        }

        setIsUploading(true);
        setErrors([]);
        let current = files;
        const newErrors: string[] = [];

        for (let i = 0; i < list.length; i++) {
            const file = list[i];
            setStatus(list.length > 1 ? "Загружаем " + (i + 1) + " из " + list.length + "…" : "Загружаем «" + file.name + "»…");

            let tags: AudioTags = {};
            try {
                tags = await readAudioTags(file);
            } catch {
                tags = {};
            }

            try {
                let uploaded = await uploadAudioFile(file, tags.title, tags.artist);

                const info: TrackInfo = {};
                if (!uploaded.cover) {
                    info.cover = tags.cover ?? randomTemplate();
                }
                if (tags.artist && uploaded.artist !== tags.artist) {
                    info.artist = tags.artist;
                }
                if (info.cover !== undefined || info.artist) {
                    try {
                        uploaded = (await saveTrackInfo(uploaded, info)).file;
                    } catch {
                        newErrors.push(file.name + ": не удалось сохранить данные из файла");
                    }
                }
                current = [uploaded, ...current];
                onFilesChange(current);
            } catch (err) {
                newErrors.push(file.name + ": " + (err instanceof Error ? err.message : "не удалось загрузить"));
            }
        }

        setErrors(newErrors);
        setStatus("");
        setIsUploading(false);
    }

    return { uploadFiles, status, errors, isUploading };
}
