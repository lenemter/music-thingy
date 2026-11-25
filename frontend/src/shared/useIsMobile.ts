import { useEffect, useState } from "react";

export const MOBILE_QUERY = "(max-width: 760px)";

export function useIsMobile() {
    const [isMobile, setIsMobile] = useState(() => window.matchMedia(MOBILE_QUERY).matches);

    useEffect(() => {
        const media = window.matchMedia(MOBILE_QUERY);
        const update = () => setIsMobile(media.matches);
        media.addEventListener("change", update);
        return () => media.removeEventListener("change", update);
    }, []);

    return isMobile;
}
