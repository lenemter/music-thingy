import { useState } from "react";
import { readAudioTags, resizeImage } from "./audioTags.ts";
import type { AudioTags } from "./audioTags.ts";
import { uploadAudioFile } from "./library.ts";
import { randomTemplate, templateKey } from "./coverTemplates.ts";
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
                const cover = tags.cover ? await resizeImage(tags.cover) : templateKey(randomTemplate());
                const uploaded = await uploadAudioFile(file, tags.title, tags.artist, cover);
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
