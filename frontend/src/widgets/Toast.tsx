import { useEffect, useState } from "react";
import { subscribeToast } from "../shared/toast.ts";
import type { ToastMessage } from "../shared/toast.ts";

const SHOW_TIME = 2600;
const HIDE_TIME = 200;

function Toast() {
    const [toast, setToast] = useState<ToastMessage | null>(null);
    const [isHiding, setIsHiding] = useState(false);

    useEffect(() => subscribeToast((next) => {
        setIsHiding(false);
        setToast(next);
    }), []);

    useEffect(() => {
        if (!toast) {
            return;
        }
        const hideTimer = setTimeout(() => setIsHiding(true), SHOW_TIME);
        const removeTimer = setTimeout(() => setToast(null), SHOW_TIME + HIDE_TIME);
        return () => {
            clearTimeout(hideTimer);
            clearTimeout(removeTimer);
        };
    }, [toast]);

    if (!toast) {
        return null;
    }

    return (
        <div key={toast.id} className={isHiding ? "toast hiding" : "toast"} role="status" aria-live="polite">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17l3 3 5.3-5.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>
            </svg>
            {toast.text}
        </div>
    )
}

export default Toast
