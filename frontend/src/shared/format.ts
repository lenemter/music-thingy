export function formatTime(seconds: number) {
    const minutes = Math.floor(seconds / 60);
    const rest = seconds % 60;

    if (rest < 10) {
        return minutes + ":0" + rest;
    }
    return minutes + ":" + rest;
}

export function plural(count: number, one: string, few: string, many: string) {
    const lastTwo = count % 100;
    const last = count % 10;
    if (lastTwo >= 11 && lastTwo <= 14) {
        return many;
    }
    if (last === 1) {
        return one;
    }
    if (last >= 2 && last <= 4) {
        return few;
    }
    return many;
}

export function trackCount(count: number) {
    return count + " " + plural(count, "трек", "трека", "треков");
}

export function formatLongTime(minutes: number) {
    const hours = Math.floor(minutes / 60);
    const rest = minutes % 60;

    if (hours === 0) {
        return rest + " мин";
    }
    return hours + " ч " + rest + " мин";
}
