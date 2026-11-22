import { fetchLikedPage } from "./api.ts";
import { sendLike, setLikedCache, takeLegacyLikes } from "./favorites.ts";
import { migrateBrowserUploads } from "./library.ts";
import { trackFromRead } from "./music/convert.ts";
import type { TrackRead } from "./music/types.ts";

const PAGE_SIZE = 100;
const MAX_PAGES = 5;

let running: Promise<void> | null = null;

async function run() {
    // Сначала переносим загрузки из браузера: у старых лайков на свои файлы меняются id
    await migrateBrowserUploads();

    for (const track of takeLegacyLikes()) {
        try {
            await sendLike(track);
        } catch {
            continue;
        }
    }

    const items: TrackRead[] = [];
    for (let page = 0; page < MAX_PAGES; page++) {
        const chunk = await fetchLikedPage(page * PAGE_SIZE, PAGE_SIZE);
        items.push(...chunk);
        if (chunk.length < PAGE_SIZE) {
            break;
        }
    }
    setLikedCache(items.map(trackFromRead));
}

// «Понравившиеся» = лайки на сайте + лайки из подключённых сервисов; сервер отдаёт их одним списком
export function syncLikes() {
    if (!running) {
        running = run().catch(() => undefined).finally(() => {
            running = null;
        });
    }
    return running;
}
