
const SKIPPED = new Set(["host", "content-length", "accept-encoding", "connection", "priority"]);

export function parseBrowserHeaders(raw: string): Record<string, string> {
    const lines = raw.split(/\r?\n/).map((line) => line.trim()).filter((line) => line !== "");
    const headers: Record<string, string> = {};

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (/^(GET|POST|PUT|OPTIONS)\s/i.test(line)) {
            continue;
        }
        const match = /^(:?[^:\s]+):\s*(.*)$/.exec(line);
        let key: string;
        let value: string;
        if (match && match[2] !== "") {
            key = match[1];
            value = match[2];
        } else {
            key = line.replace(/:$/, "");
            value = lines[i + 1] ?? "";
            i++;
        }
        key = key.toLowerCase();
        if (key.startsWith(":") || SKIPPED.has(key)) {
            continue;
        }
        headers[key] = value;
    }

    if (!headers["x-goog-authuser"]) {
        headers["x-goog-authuser"] = "0";
    }
    return headers;
}

export function validateBrowserHeaders(headers: Record<string, string>): string | null {
    const cookie = headers.cookie ?? "";
    if (cookie === "") {
        return "В заголовках нет cookie — скопируйте заголовки запроса целиком";
    }
    if (!cookie.includes("__Secure-3PAPISID")) {
        return "В cookie нет данных входа — проверьте, что вы вошли в аккаунт на music.youtube.com";
    }
    if (!(headers.authorization ?? "").includes("SAPISIDHASH")) {
        return "Нет заголовка authorization — скопируйте заголовки именно запроса browse (POST), а не страницы";
    }
    return null;
}
