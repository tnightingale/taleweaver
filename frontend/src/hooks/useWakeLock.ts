import { useRef, useEffect } from "react";

/**
 * Requests a screen wake lock while `active` is true.
 * Prevents the device from dimming/locking the screen during audio playback.
 * Automatically re-acquires the lock when the page regains visibility
 * (the browser releases wake locks when a tab is hidden).
 */
export function useWakeLock(active: boolean) {
  const wakeLockRef = useRef<WakeLockSentinel | null>(null);

  useEffect(() => {
    if (!("wakeLock" in navigator)) return;

    const request = async () => {
      try {
        wakeLockRef.current = await navigator.wakeLock.request("screen");
        wakeLockRef.current.addEventListener("release", () => {
          wakeLockRef.current = null;
        });
      } catch {
        // Wake lock request can fail (e.g. low battery mode) — not critical
      }
    };

    const handleVisibilityChange = () => {
      if (active && document.visibilityState === "visible" && !wakeLockRef.current) {
        request();
      }
    };

    if (active) {
      request();
      document.addEventListener("visibilitychange", handleVisibilityChange);
    } else {
      wakeLockRef.current?.release();
      wakeLockRef.current = null;
    }

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      wakeLockRef.current?.release();
      wakeLockRef.current = null;
    };
  }, [active]);
}
