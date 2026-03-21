import { useState } from "react";
import { motion } from "framer-motion";
import type { StoryMetadata } from "../types";

interface Props {
  story: StoryMetadata;
  onPlay: () => void;
  onDelete: () => void;
  onUpdateTitle: (newTitle: string) => Promise<void>;
}

const formatDuration = (seconds: number) => {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
};

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString();
};

export default function StoryCard({ story, onPlay, onDelete, onUpdateTitle }: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState(story.title);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const handleSaveTitle = async () => {
    if (editedTitle.trim() && editedTitle !== story.title) {
      setIsSaving(true);
      try {
        await onUpdateTitle(editedTitle.trim());
      } catch (err) {
        // Reset on error
        setEditedTitle(story.title);
      }
      setIsSaving(false);
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSaveTitle();
    } else if (e.key === "Escape") {
      setEditedTitle(story.title);
      setIsEditing(false);
    }
  };

  const handleDelete = () => {
    setIsDeleting(true);
    onDelete();
  };

  const getTypeLabel = () => {
    if (story.story_type === "historical") return "Historical";
    return story.genre || "Custom";
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ y: -4 }}
      className="glass-card p-4 flex flex-col gap-3 relative"
    >
      {/* Title */}
      {isEditing ? (
        <div className="relative">
          <input
            type="text"
            value={editedTitle}
            onChange={(e) => setEditedTitle(e.target.value)}
            onBlur={handleSaveTitle}
            onKeyDown={handleKeyDown}
            autoFocus
            disabled={isSaving}
            className="text-lg font-display text-glow bg-black/50 border border-purple-500/50 
                       rounded px-2 py-1 text-white focus:outline-none focus:border-purple-400 w-full
                       disabled:opacity-50"
            placeholder="Story title"
          />
          <div className="text-xs text-starlight/40 mt-1">
            Press Enter to save, Esc to cancel
          </div>
        </div>
      ) : (
        <h3 className="text-lg font-display text-glow line-clamp-2 min-h-[3.5rem]">
          {story.title}
        </h3>
      )}

      {/* Metadata */}
      <div className="flex items-center gap-2 text-sm text-starlight/60">
        <span>{story.kid_name}, {story.kid_age}</span>
        <span>•</span>
        <span>{getTypeLabel()}</span>
        <span>•</span>
        <span>{formatDuration(story.duration_seconds)}</span>
      </div>

      {/* Date */}
      <div className="text-xs text-starlight/40">
        {formatDate(story.created_at)}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-2 mt-2">
        <button
          onClick={onPlay}
          className="flex-1 px-3 py-2 bg-purple-600 hover:bg-purple-500 rounded 
                     text-white text-sm font-semibold transition-all
                     hover:shadow-lg hover:shadow-purple-500/50"
          disabled={isDeleting}
        >
          ▶ Play
        </button>
        <button
          onClick={() => navigator.clipboard.writeText(`${window.location.origin}${story.permalink}`)}
          className="px-3 py-2 bg-black/50 hover:bg-black/70 border border-purple-500/30 
                     rounded text-purple-300 text-sm transition-all"
          title="Copy permalink"
          disabled={isDeleting}
        >
          🔗
        </button>
        <a
          href={story.audio_url}
          download={`${story.title}.mp3`}
          className="px-3 py-2 bg-black/50 hover:bg-black/70 border border-purple-500/30 
                     rounded text-purple-300 text-sm transition-all"
          title="Download MP3"
        >
          📥
        </a>
      </div>

      {/* Edit & Delete Row */}
      <div className="flex gap-2">
        <button
          onClick={() => setIsEditing(true)}
          className="flex-1 px-3 py-1 bg-black/30 hover:bg-black/50 border border-purple-500/20 
                     rounded text-purple-400 text-xs transition-all"
          disabled={isEditing || isDeleting}
        >
          ✏️ Edit Title
        </button>
        <button
          onClick={handleDelete}
          className="flex-1 px-3 py-1 bg-red-900/30 hover:bg-red-900/50 border border-red-500/30 
                     rounded text-red-400 text-xs transition-all"
          disabled={isDeleting}
        >
          {isDeleting ? "Deleting..." : "🗑️ Delete"}
        </button>
      </div>
    </motion.div>
  );
}
