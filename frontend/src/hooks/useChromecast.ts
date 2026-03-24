import { useState, useEffect, useCallback, useRef } from "react";
import type { Scene } from "../types";

interface CastMediaOptions {
  audioUrl: string;
  title: string;
  artwork?: string;
  scenes?: Scene[];
}

interface ChromecastAPI {
  isAvailable: boolean;
  isConnected: boolean;
  deviceName: string | null;
  isPaused: boolean;
  currentTime: number;
  duration: number;
  cast: (options: CastMediaOptions) => void;
  playOrPause: () => void;
  seek: (time: number) => void;
  disconnect: () => void;
}

export function useChromecast(): ChromecastAPI {
  const [isAvailable, setIsAvailable] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [deviceName, setDeviceName] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const playerRef = useRef<cast.framework.RemotePlayer | null>(null);
  const controllerRef = useRef<cast.framework.RemotePlayerController | null>(
    null
  );
  const pendingMediaRef = useRef<CastMediaOptions | null>(null);

  // Initialize Cast SDK when it becomes available
  useEffect(() => {
    const initCast = (available: boolean) => {
      if (!available) return;

      const context = cast.framework.CastContext.getInstance();
      context.setOptions({
        receiverApplicationId:
          chrome.cast.media.DEFAULT_MEDIA_RECEIVER_APP_ID,
        autoJoinPolicy: chrome.cast.AutoJoinPolicy.ORIGIN_SCOPED,
      });

      const player = new cast.framework.RemotePlayer();
      const controller = new cast.framework.RemotePlayerController(player);
      playerRef.current = player;
      controllerRef.current = controller;

      // Listen for remote player changes
      const onChange = (event: cast.framework.RemotePlayerChangedEvent) => {
        switch (event.field) {
          case "isConnected":
            setIsConnected(player.isConnected);
            if (player.isConnected) {
              const session = context.getCurrentSession();
              setDeviceName(
                session?.getCastDevice()?.friendlyName ?? null
              );
              // If we have pending media to load, do it now
              if (pendingMediaRef.current) {
                loadMediaOnSession(session, pendingMediaRef.current);
                pendingMediaRef.current = null;
              }
            } else {
              setDeviceName(null);
            }
            break;
          case "isPaused":
            setIsPaused(player.isPaused);
            break;
          case "currentTime":
            setCurrentTime(player.currentTime);
            break;
          case "duration":
            setDuration(player.duration);
            break;
        }
      };

      controller.addEventListener(
        cast.framework.RemotePlayerEventType.ANY_CHANGE,
        onChange
      );

      setIsAvailable(true);

      return () => {
        controller.removeEventListener(
          cast.framework.RemotePlayerEventType.ANY_CHANGE,
          onChange
        );
      };
    };

    // The Cast SDK calls this global when ready
    if (
      typeof window !== "undefined" &&
      typeof cast !== "undefined" &&
      cast.framework
    ) {
      // SDK already loaded
      initCast(true);
    } else {
      // Wait for SDK to load
      window.__onGCastApiAvailable = initCast;
    }
  }, []);

  const loadMediaOnSession = useCallback(
    (
      session: cast.framework.CastSession | null,
      options: CastMediaOptions
    ) => {
      if (!session) return;

      const mediaInfo = new chrome.cast.media.MediaInfo(
        options.audioUrl,
        "audio/mpeg"
      );

      const metadata = new chrome.cast.media.GenericMediaMetadata();
      metadata.title = options.title;
      metadata.subtitle = "Taleweaver";
      if (options.artwork) {
        metadata.images = [{ url: options.artwork }];
      }
      mediaInfo.metadata = metadata;

      // Pass scene data for future custom receiver (Phase 3)
      if (options.scenes) {
        mediaInfo.customData = {
          scenes: options.scenes.map((s) => ({
            image_url: s.image_url
              ? new URL(s.image_url, window.location.origin).href
              : null,
            beat_name: s.beat_name,
            timestamp_start: s.timestamp_start,
            timestamp_end: s.timestamp_end,
          })),
        };
      }

      const request = new chrome.cast.media.LoadRequest(mediaInfo);
      request.autoplay = true;

      session.loadMedia(request).catch((err) => {
        console.error("Cast loadMedia failed:", err);
      });
    },
    []
  );

  const castMedia = useCallback(
    (options: CastMediaOptions) => {
      const context = cast.framework.CastContext.getInstance();
      const session = context.getCurrentSession();

      if (session) {
        // Already connected — just load media
        loadMediaOnSession(session, options);
      } else {
        // Store media for after session starts
        pendingMediaRef.current = options;
        context.requestSession().catch((err) => {
          console.error("Cast requestSession failed:", err);
          pendingMediaRef.current = null;
        });
      }
    },
    [loadMediaOnSession]
  );

  const playOrPause = useCallback(() => {
    controllerRef.current?.playOrPause();
  }, []);

  const seek = useCallback((time: number) => {
    const player = playerRef.current;
    const controller = controllerRef.current;
    if (player && controller) {
      player.currentTime = time;
      controller.seek();
    }
  }, []);

  const disconnect = useCallback(() => {
    cast.framework.CastContext.getInstance().endCurrentSession(true);
  }, []);

  return {
    isAvailable,
    isConnected,
    deviceName,
    isPaused,
    currentTime,
    duration,
    cast: castMedia,
    playOrPause,
    seek,
    disconnect,
  };
}
