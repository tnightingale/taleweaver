import { useState, useEffect, useCallback, type RefObject } from "react";

interface FullscreenAPI {
  isFullscreen: boolean;
  toggleFullscreen: () => void;
  isSupported: boolean;
}

export function useFullscreen(elementRef: RefObject<HTMLElement | null>): FullscreenAPI {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const isSupported =
    typeof document !== "undefined" &&
    (!!document.fullscreenEnabled ||
      !!(document as unknown as { webkitFullscreenEnabled: boolean }).webkitFullscreenEnabled);

  useEffect(() => {
    const onChange = () => {
      const fsElement =
        document.fullscreenElement ||
        (document as unknown as { webkitFullscreenElement: Element | null }).webkitFullscreenElement;
      setIsFullscreen(!!fsElement);
    };

    document.addEventListener("fullscreenchange", onChange);
    document.addEventListener("webkitfullscreenchange", onChange);
    return () => {
      document.removeEventListener("fullscreenchange", onChange);
      document.removeEventListener("webkitfullscreenchange", onChange);
    };
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (!elementRef.current || !isSupported) return;

    const fsElement =
      document.fullscreenElement ||
      (document as unknown as { webkitFullscreenElement: Element | null }).webkitFullscreenElement;

    if (fsElement) {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if ((document as unknown as { webkitExitFullscreen: () => void }).webkitExitFullscreen) {
        (document as unknown as { webkitExitFullscreen: () => void }).webkitExitFullscreen();
      }
    } else {
      const el = elementRef.current as HTMLElement & { webkitRequestFullscreen?: () => Promise<void> };
      if (el.requestFullscreen) {
        el.requestFullscreen();
      } else if (el.webkitRequestFullscreen) {
        el.webkitRequestFullscreen();
      }
    }
  }, [elementRef, isSupported]);

  return { isFullscreen, toggleFullscreen, isSupported };
}
