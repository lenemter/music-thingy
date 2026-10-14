export function formatTime(seconds: number) {
    const minutes = Math.floor(seconds / 60);
    const rest = seconds % 60;

    if (rest < 10) {
        return minutes + ":0" + rest;
    }
    return minutes + ":" + rest;
}

export function formatLongTime(minutes: number) {
    const hours = Math.floor(minutes / 60);
    const rest = minutes % 60;

    if (hours === 0) {
        return rest + " мин";
    }
    return hours + " ч " + rest + " мин";
}
