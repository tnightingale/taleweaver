import { useEffect, useState } from "react";
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
  const { isOffline } = useOfflineStatus();

  useEffect(() => {
    if (!shortId) return;

    fetch(`/api/permalink/${shortId}`)
      .then((res) => {
        if (!res.ok) throw new Error("Story not found");
        return res.json();
      })
      .then((data: StoryMetadata) => {
        setStory(data);
        setLoading(false);
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
      />
    </>
  );
}
