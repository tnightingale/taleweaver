import { useState, useEffect, useCallback, type RefObject } from "react";

interface AirPlayAPI {
  isAvailable: boolean;
  isActive: boolean;
  showPicker: () => void;
}

// WebKit-specific types for AirPlay
interface WebKitAudioElement extends HTMLAudioElement {
  webkitShowPlaybackTargetPicker?: () => void;
}

export function useAirPlay(audioRef: RefObject<HTMLAudioElement | null>): AirPlayAPI {
  const [isAvailable, setIsAvailable] = useState(false);
  const [isActive, setIsActive] = useState(false);

  useEffect(() => {
    // Check if AirPlay is supported (Safari/WebKit only)
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
      const webkitAudio = audio as WebKitAudioElement & {
        webkitCurrentPlaybackTargetIsWireless?: boolean;
      };
      setIsActive(webkitAudio.webkitCurrentPlaybackTargetIsWireless ?? false);
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
    const audio = audioRef.current as WebKitAudioElement | null;
    audio?.webkitShowPlaybackTargetPicker?.();
  }, [audioRef]);

  return { isAvailable, isActive, showPicker };
}
