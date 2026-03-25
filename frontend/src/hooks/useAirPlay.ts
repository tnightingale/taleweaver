import { useState, useEffect, useCallback, type RefObject } from "react";

interface AirPlayAPI {
  isAvailable: boolean;
  isActive: boolean;
  showPicker: () => void;
}

// WebKit-specific types for AirPlay
interface WebKitMediaElement extends HTMLMediaElement {
  webkitShowPlaybackTargetPicker?: () => void;
  webkitCurrentPlaybackTargetIsWireless?: boolean;
}

function isIOSDevice(): boolean {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

export function useAirPlay(audioRef: RefObject<HTMLMediaElement | null>): AirPlayAPI {
  const [isAvailable, setIsAvailable] = useState(false);
  const [isActive, setIsActive] = useState(false);

  useEffect(() => {
    // On iOS, all browsers use WebKit and can AirPlay.
    // Chrome iOS doesn't reliably fire webkitplaybacktargetavailabilitychanged,
    // so we optimistically show the button on all iOS devices.
    if (isIOSDevice()) {
      setIsAvailable(true);
    }

    if (!("WebKitPlaybackTargetAvailabilityEvent" in window)) return;

    const audio = audioRef.current;
    if (!audio) return;

    const onAvailability = (e: Event) => {
      const evt = e as Event & { availability: string };
      setIsAvailable(evt.availability === "available");
    };

    const onTargetChanged = () => {
      // When the target changes, we're either casting or back to local
      // Safari fires this event when AirPlay connects/disconnects
      const webkitMedia = audio as WebKitMediaElement;
      setIsActive(webkitMedia.webkitCurrentPlaybackTargetIsWireless ?? false);
    };

    audio.addEventListener(
      "webkitplaybacktargetavailabilitychanged",
      onAvailability
    );
    audio.addEventListener(
      "webkitcurrentplaybacktargetiswirelesschanged",
      onTargetChanged
    );

    return () => {
      audio.removeEventListener(
        "webkitplaybacktargetavailabilitychanged",
        onAvailability
      );
      audio.removeEventListener(
        "webkitcurrentplaybacktargetiswirelesschanged",
        onTargetChanged
      );
    };
  }, [audioRef]);

  const showPicker = useCallback(() => {
    const media = audioRef.current as WebKitMediaElement | null;
    media?.webkitShowPlaybackTargetPicker?.();
  }, [audioRef]);

  return { isAvailable, isActive, showPicker };
}
