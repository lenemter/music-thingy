export type Route = {
    page: "home" | "search" | "library"
    playlistId: string | null
    query: string
}

export const homeRoute: Route = { page: "home", playlistId: null, query: "" };

export function routeToHash(route: Route) {
    const base = route.playlistId
        ? "#/playlist/" + encodeURIComponent(route.playlistId)
        : route.page === "library" ? "#/library" : "#/";
    if (route.query) {
        return base + (base.endsWith("/") ? "" : "/") + "search/" + encodeURIComponent(route.query);
    }
    if (route.page === "search" && !route.playlistId) {
        return "#/search";
    }
    return base;
}

export function parseHash(hash: string): Route {
    const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
    const route: Route = { ...homeRoute };
    let index = 0;

    if (parts[index] === "library") {
        route.page = "library";
        index += 1;
    } else if (parts[index] === "playlist" && parts[index + 1]) {
        route.page = "library";
        route.playlistId = safeDecode(parts[index + 1]);
        index += 2;
    } else if (parts[index] === "search") {
        route.page = "search";
    }
    if (parts[index] === "search" && parts[index + 1]) {
        route.query = safeDecode(parts.slice(index + 1).join("/"));
    }
    return route;
}

function safeDecode(text: string) {
    try {
        return decodeURIComponent(text);
    } catch {
        return text;
    }
}
