import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import type { StoryMetadata } from "../types";
import StoryScreen from "./StoryScreen";

export default function StandalonePlayer() {
  const { shortId } = useParams<{ shortId: string }>();
  const navigate = useNavigate();
  const [story, setStory] = useState<StoryMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!shortId) return;

    fetch(`/s/${shortId}`)
      .then((res) => {
        if (!res.ok) throw new Error("Story not found");
        return res.json();
      })
      .then((data: StoryMetadata) => {
        setStory(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load story");
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
          <div className="text-6xl mb-4">😔</div>
          <h2 className="text-2xl font-display text-glow mb-2">Story Not Found</h2>
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

  // Render the story using StoryScreen component
  return (
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
      }}
      onCreateAnother={() => navigate("/")}
    />
  );
}
