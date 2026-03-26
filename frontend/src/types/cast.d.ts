// Ambient type declarations for the Google Cast SDK (subset used by Story Spring)
// Full SDK loaded externally via <script> tag

declare namespace cast {
  namespace framework {
    class CastContext {
      static getInstance(): CastContext;
      setOptions(options: CastOptions): void;
      getCurrentSession(): CastSession | null;
      requestSession(): Promise<void>;
      endCurrentSession(stopCasting: boolean): void;
      addEventListener(
        type: CastContextEventType,
        handler: (event: { sessionState: SessionState }) => void
      ): void;
      removeEventListener(
        type: CastContextEventType,
        handler: (event: { sessionState: SessionState }) => void
      ): void;
    }

    class CastSession {
      getSessionObj(): chrome.cast.Session;
      getMediaSession(): chrome.cast.media.Media | null;
      loadMedia(
        request: chrome.cast.media.LoadRequest
      ): Promise<chrome.cast.ErrorCode | void>;
      getCastDevice(): { friendlyName: string };
    }

    class RemotePlayer {
      isConnected: boolean;
      isPaused: boolean;
      currentTime: number;
      duration: number;
      volumeLevel: number;
      canSeek: boolean;
    }

    class RemotePlayerController {
      constructor(player: RemotePlayer);
      playOrPause(): void;
      seek(): void;
      stop(): void;
      addEventListener(
        type: RemotePlayerEventType,
        handler: (event: RemotePlayerChangedEvent) => void
      ): void;
      removeEventListener(
        type: RemotePlayerEventType,
        handler: (event: RemotePlayerChangedEvent) => void
      ): void;
    }

    interface CastOptions {
      receiverApplicationId: string;
      autoJoinPolicy: chrome.cast.AutoJoinPolicy;
    }

    interface RemotePlayerChangedEvent {
      field: string;
      value: unknown;
    }

    enum CastContextEventType {
      SESSION_STATE_CHANGED = "sessionstatechanged",
    }

    enum RemotePlayerEventType {
      ANY_CHANGE = "anyChanged",
    }

    enum SessionState {
      NO_SESSION = "NO_SESSION",
      SESSION_STARTING = "SESSION_STARTING",
      SESSION_STARTED = "SESSION_STARTED",
      SESSION_START_FAILED = "SESSION_START_FAILED",
      SESSION_ENDING = "SESSION_ENDING",
      SESSION_ENDED = "SESSION_ENDED",
      SESSION_RESUMED = "SESSION_RESUMED",
    }
  }
}

declare namespace chrome {
  namespace cast {
    enum AutoJoinPolicy {
      ORIGIN_SCOPED = "origin_scoped",
      TAB_AND_ORIGIN_SCOPED = "tab_and_origin_scoped",
      PAGE_SCOPED = "page_scoped",
    }

    enum ErrorCode {
      CANCEL = "cancel",
      TIMEOUT = "timeout",
      API_NOT_INITIALIZED = "api_not_initialized",
      INVALID_PARAMETER = "invalid_parameter",
      EXTENSION_NOT_COMPATIBLE = "extension_not_compatible",
      EXTENSION_MISSING = "extension_missing",
      RECEIVER_UNAVAILABLE = "receiver_unavailable",
      SESSION_ERROR = "session_error",
      CHANNEL_ERROR = "channel_error",
      LOAD_MEDIA_FAILED = "load_media_failed",
    }

    class Session {
      receiver: { friendlyName: string };
    }

    namespace media {
      const DEFAULT_MEDIA_RECEIVER_APP_ID: string;

      class MediaInfo {
        constructor(contentId: string, contentType: string);
        metadata: GenericMediaMetadata | null;
        customData: unknown;
      }

      class LoadRequest {
        constructor(mediaInfo: MediaInfo);
        autoplay: boolean;
        currentTime: number;
        customData: unknown;
      }

      class GenericMediaMetadata {
        title: string;
        subtitle: string;
        images: Array<{ url: string }>;
      }

      class Media {
        currentTime: number;
        duration: number;
        playerState: string;
      }
    }
  }
}

// Global callback for Cast SDK availability
interface Window {
  __onGCastApiAvailable?: (isAvailable: boolean) => void;
}
