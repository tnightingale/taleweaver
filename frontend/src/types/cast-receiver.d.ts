// Ambient type declarations for the Google Cast Receiver SDK v3
// Used by the cast-receiver app only

declare namespace cast {
  namespace framework {
    class CastReceiverContext {
      static getInstance(): CastReceiverContext;
      getPlayerManager(): PlayerManager;
      start(): void;
    }

    class PlayerManager {
      getDurationSec(): number;
      getCurrentTimeSec(): number;
      setMessageInterceptor(
        type: messages.MessageType,
        interceptor: (request: messages.LoadRequestData) => messages.LoadRequestData
      ): void;
      addEventListener(
        type: events.EventType,
        handler: (event: events.Event) => void
      ): void;
    }

    namespace messages {
      enum MessageType {
        LOAD = "LOAD",
      }

      interface LoadRequestData {
        media?: MediaInformation;
        [key: string]: unknown;
      }

      interface MediaInformation {
        contentId: string;
        contentType: string;
        customData?: unknown;
        metadata?: {
          title?: string;
          [key: string]: unknown;
        };
      }
    }

    namespace events {
      enum EventType {
        TIME_UPDATE = "TIME_UPDATE",
        MEDIA_FINISHED = "MEDIA_FINISHED",
        PLAYING = "PLAYING",
      }

      interface Event {
        type: EventType;
      }

      interface MediaElementEvent extends Event {
        currentMediaTime: number;
      }
    }
  }
}
