import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import type { StoryMetadata } from "../types";
import { useOfflineStatus } from "../hooks/useOfflineStatus";
import StoryScreen from "./StoryScreen";

export default function StandalonePlayer() {
  const { shortId } = useParams<{ shortId: string }>();
  const navigate = useNavigate();
  const [story, setStory] = useState<StoryMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cachedOffline, setCachedOffline] = useState(false);
  const cachedOfflineRef = useRef(false);
  const { isOffline } = useOfflineStatus();

  // Listen for SW confirmation that audio is cached
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return;
    const handler = (event: MessageEvent) => {
      if (event.data?.type === 'AUDIO_CACHED') {
        cachedOfflineRef.current = true;
        setCachedOffline(true);
        setTimeout(() => setCachedOffline(false), 3000);
      }
    };
    navigator.serviceWorker.addEventListener('message', handler);
    return () => navigator.serviceWorker.removeEventListener('message', handler);
  }, []);

  useEffect(() => {
    if (!shortId) return;

    const metadataUrl = `/api/permalink/${shortId}`;
    fetch(metadataUrl)
      .then(async (res) => {
        if (!res.ok) throw new Error("Story not found");

        // Cache the metadata response directly from the page.
        // This is critical because on first visit, the SW may not be active yet
        // so it won't intercept this fetch. Without this, the story-metadata
        // cache is empty and offline refresh fails.
        if ('caches' in window) {
          try {
            const cache = await caches.open('story-metadata');
            await cache.put(metadataUrl, res.clone());
          } catch { /* best effort */ }
        }

        return res.json();
      })
      .then((data: StoryMetadata) => {
        setStory(data);
        setLoading(false);

        // Prefetch audio for offline using two approaches:
        // 1. postMessage to SW (preferred — SW caches + sends AUDIO_CACHED confirmation)
        // 2. Direct fetch fallback (ensures audio goes through SW fetch handler which caches it)
        // Both are needed because iOS Safari has timing issues with postMessage on first load.
        if (data.audio_url) {
          const audioUrl = data.audio_url;

          // Approach 1: Ask SW directly
          if ('serviceWorker' in navigator) {
            navigator.serviceWorker.ready.then((reg) => {
              reg.active?.postMessage({ type: 'PREFETCH_AUDIO', url: audioUrl });
            });
          }

          // Approach 2: Direct fetch (goes through SW fetch handler → CacheFirst caches it)
          // Small delay to let the SW activate and register its routes first
          setTimeout(() => {
            fetch(audioUrl).then(() => {
              // If the SW postMessage path didn't fire the toast, check cache directly
              if ('caches' in window) {
                caches.open('story-audio').then((cache) =>
                  cache.match(audioUrl).then((cached) => {
                    if (cached && !cachedOfflineRef.current) {
                      setCachedOffline(true);
                      setTimeout(() => setCachedOffline(false), 3000);
                    }
                  })
                );
              }
            }).catch(() => {});
          }, 1000);
        }
      })
      .catch((err) => {
        // If offline and fetch failed, the SW cache missed
        if (!navigator.onLine) {
          setError("This story isn't available offline yet. Visit it once while online to save it for offline listening.");
        } else {
          setError(err.message || "Failed to load story");
        }
        setLoading(false);
      });
  }, [shortId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center"
        >
          <div className="text-4xl mb-4">📖</div>
          <p className="text-starlight/60">Loading story...</p>
        </motion.div>
      </div>
    );
  }

  if (error || !story) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center glass-card p-8 max-w-md"
        >
          <div className="text-6xl mb-4">{isOffline ? "📡" : "😔"}</div>
          <h2 className="text-2xl font-display text-glow mb-2">
            {isOffline ? "Offline" : "Story Not Found"}
          </h2>
          <p className="text-starlight/60 mb-6">
            {error || "This story doesn't exist or may have been deleted."}
          </p>
          <button onClick={() => navigate("/")} className="btn-glow">
            Create Your Own Story
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <>
      {isOffline && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-purple-900/90 text-starlight text-center text-xs py-1.5 backdrop-blur-sm">
          Offline — playing cached version
        </div>
      )}
      {cachedOffline && !isOffline && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className="fixed top-3 left-1/2 -translate-x-1/2 z-50
                     bg-green-900/90 text-green-100 text-xs px-4 py-2 rounded-full
                     backdrop-blur-sm shadow-lg flex items-center gap-2"
        >
          <span>Available offline</span>
        </motion.div>
      )}
      <StoryScreen
        isGenerating={false}
        title={story.title}
        audioUrl={story.audio_url}
        durationSeconds={story.duration_seconds}
        transcript={story.transcript}
        storyData={{
          job_id: story.id,
          status: "complete",
          title: story.title,
          duration_seconds: story.duration_seconds,
          audio_url: story.audio_url,
          transcript: story.transcript,
          short_id: story.short_id,
          permalink: story.permalink,
          has_illustrations: story.has_illustrations || false,
          art_style: story.art_style,
          scenes: story.scenes,
        }}
        onCreateAnother={() => navigate("/")}
        onBackToLibrary={() => navigate("/library")}
      />
    </>
  );
}
