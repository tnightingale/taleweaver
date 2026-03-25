import { useEffect, useRef } from "react";

interface MediaSessionOptions {
  title: string;
  artist?: string;
  artwork?: string;
  isPlaying: boolean;
  duration: number;
  currentTime: number;
  onPlay: () => void;
  onPause: () => void;
  onSeekTo: (time: number) => void;
}

export function useMediaSession({
  title,
  artist = "Taleweaver",
  artwork,
  isPlaying,
  duration,
  currentTime,
  onPlay,
  onPause,
  onSeekTo,
}: MediaSessionOptions) {
  const callbacksRef = useRef({ onPlay, onPause, onSeekTo });
  callbacksRef.current = { onPlay, onPause, onSeekTo };

  // Set metadata when title or artwork changes
  useEffect(() => {
    if (!("mediaSession" in navigator)) return;

    const artworkList: MediaImage[] = artwork
      ? [{ src: artwork, sizes: "512x512", type: "image/png" }]
      : [];

    navigator.mediaSession.metadata = new MediaMetadata({
      title,
      artist,
      artwork: artworkList,
    });
  }, [title, artist, artwork]);

  // Register action handlers
  useEffect(() => {
    if (!("mediaSession" in navigator)) return;

    const handlers: [MediaSessionAction, MediaSessionActionHandler][] = [
      ["play", () => callbacksRef.current.onPlay()],
      ["pause", () => callbacksRef.current.onPause()],
      [
        "seekto",
        (details) => {
          if (details.seekTime != null) {
            callbacksRef.current.onSeekTo(details.seekTime);
          }
        },
      ],
      [
        "seekbackward",
        () => {
          // Seek back 10 seconds
          callbacksRef.current.onSeekTo(Math.max(0, currentTime - 10));
        },
      ],
      [
        "seekforward",
        () => {
          // Seek forward 10 seconds
          callbacksRef.current.onSeekTo(Math.min(duration, currentTime + 10));
        },
      ],
    ];

    for (const [action, handler] of handlers) {
      try {
        navigator.mediaSession.setActionHandler(action, handler);
      } catch {
        // Action not supported
      }
    }

    return () => {
      for (const [action] of handlers) {
        try {
          navigator.mediaSession.setActionHandler(action, null);
        } catch {
          // Ignore
        }
      }
    };
  }, [currentTime, duration]);

  // Update playback state and position
  useEffect(() => {
    if (!("mediaSession" in navigator)) return;

    navigator.mediaSession.playbackState = isPlaying ? "playing" : "paused";

    if (duration > 0 && isFinite(duration)) {
      try {
        navigator.mediaSession.setPositionState({
          duration,
          playbackRate: 1,
          position: Math.min(currentTime, duration),
        });
      } catch {
        // Position state not supported
      }
    }
  }, [isPlaying, currentTime, duration]);
}
