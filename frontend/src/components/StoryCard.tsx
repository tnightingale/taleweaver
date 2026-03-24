import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { StoryMetadata } from "../types";
import { regenerateIllustrations, pollJobStatus } from "../api/client";
import ArtStylePickerModal from "./ArtStylePickerModal";
import ConfirmDialog from "./ConfirmDialog";

interface Props {
  story: StoryMetadata;
  onPlay: () => void;
  onDelete: () => void;
  onUpdateTitle: (newTitle: string) => Promise<void>;
  onRegenerationComplete?: () => void;
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

export default function StoryCard({ story, onPlay, onDelete, onUpdateTitle, onRegenerationComplete }: Props) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState(story.title);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [cachedOffline, setCachedOffline] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [regenStatus, setRegenStatus] = useState("");
  const [showStylePicker, setShowStylePicker] = useState<"add" | "all" | null>(null);
  const [showConfirmRegenAll, setShowConfirmRegenAll] = useState<{ artStyle: string; customPrompt?: string } | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const regenPollingRef = useRef<ReturnType<typeof setInterval>>(undefined);

  // Clean up regeneration polling on unmount
  useEffect(() => {
    return () => {
      if (regenPollingRef.current) clearInterval(regenPollingRef.current);
    };
  }, []);

  // Close menu on outside click
  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  // Check if this story's audio is cached for offline
  useEffect(() => {
    if (!('caches' in window) || !story.audio_url) return;
    caches.open('story-audio').then((cache) =>
      cache.match(story.audio_url).then((r) => {
        if (r) setCachedOffline(true);
      })
    ).catch(() => {});
  }, [story.audio_url]);

  const handleSaveTitle = async () => {
    if (editedTitle.trim() && editedTitle !== story.title) {
      setIsSaving(true);
      try {
        await onUpdateTitle(editedTitle.trim());
      } catch {
        setEditedTitle(story.title);
      }
      setIsSaving(false);
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSaveTitle();
    else if (e.key === "Escape") {
      setEditedTitle(story.title);
      setIsEditing(false);
    }
  };

  const handleCopyLink = async () => {
    const url = `${window.location.origin}${story.permalink}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const input = document.createElement("input");
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
    setMenuOpen(false);
  };

  const handleDelete = () => {
    if (!confirm("Delete this story? This cannot be undone.")) return;
    setIsDeleting(true);
    setMenuOpen(false);
    onDelete();
  };

  const getTypeLabel = () => {
    if (story.story_type === "historical") return "Historical";
    return story.genre || "Custom";
  };

  const hasMissingImages = story.art_style && story.scenes?.some(s => !s.image_url);
  const hasIllustrations = story.art_style && story.scenes && story.scenes.length > 0;
  const hasNoIllustrations = !story.art_style || !story.scenes;

  const handleIllustrationAction = async (
    mode: "missing" | "all" | "add" | "single",
    artStyle?: string,
    customPrompt?: string,
  ) => {
    setIsRegenerating(true);
    setRegenStatus("Starting...");
    setMenuOpen(false);
    try {
      const options: { mode: typeof mode; art_style?: string; custom_art_style_prompt?: string } = { mode };
      if (artStyle) options.art_style = artStyle;
      if (customPrompt) options.custom_art_style_prompt = customPrompt;
      const result = await regenerateIllustrations(story.short_id, options);
      if (result.message) {
        setRegenStatus(result.message);
        setTimeout(() => { setIsRegenerating(false); setRegenStatus(""); }, 2000);
        return;
      }

      const label = mode === "add" ? "Adding illustrations..." : `Regenerating ${result.failed_count} images...`;
      setRegenStatus(label);
      regenPollingRef.current = setInterval(async () => {
        try {
          const status = await pollJobStatus(result.job_id);
          if (status.status === "complete") {
            if (regenPollingRef.current) clearInterval(regenPollingRef.current);
            setRegenStatus("Done!");
            onRegenerationComplete?.();
            setTimeout(() => { setIsRegenerating(false); setRegenStatus(""); }, 1500);
          } else if (status.status === "failed") {
            if (regenPollingRef.current) clearInterval(regenPollingRef.current);
            const errorMsg = "error" in status ? status.error : "Regeneration failed";
            setRegenStatus(errorMsg || "Regeneration failed");
            setTimeout(() => { setIsRegenerating(false); setRegenStatus(""); }, 3000);
          } else if ("progress_detail" in status && status.progress_detail) {
            setRegenStatus(status.progress_detail);
          }
        } catch {
          if (regenPollingRef.current) clearInterval(regenPollingRef.current);
          setRegenStatus("Failed to check status");
          setTimeout(() => { setIsRegenerating(false); setRegenStatus(""); }, 3000);
        }
      }, 2000);
    } catch (err) {
      setRegenStatus(err instanceof Error ? err.message : "Failed");
      setTimeout(() => { setIsRegenerating(false); setRegenStatus(""); }, 3000);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ y: -4 }}
      className="glass-card flex flex-col relative"
    >
      {/* Cover Image — overflow-hidden scoped to just the image, not the whole card */}
      {story.cover_image_url ? (
        <div className="aspect-[3/2] w-full overflow-hidden cursor-pointer relative group rounded-t-[1rem]" onClick={onPlay}>
          <img
            src={story.cover_image_url}
            alt={story.title}
            loading="lazy"
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
          <div className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/20 transition-colors">
            <div className="w-12 h-12 rounded-full bg-black/50 backdrop-blur-sm
                            flex items-center justify-center text-white
                            opacity-70 group-hover:opacity-100 transition-opacity
                            shadow-[0_0_20px_rgba(0,0,0,0.3)]">
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 ml-0.5"><path d="M6 4l10 6-10 6z" /></svg>
            </div>
          </div>
          {/* Offline badge */}
          {cachedOffline && (
            <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded-full
                            bg-purple-900/80 text-purple-200 text-[9px] backdrop-blur-sm
                            border border-purple-500/20">
              Offline
            </div>
          )}
        </div>
      ) : (
        <div
          className="aspect-[3/2] w-full flex items-center justify-center cursor-pointer relative group
                     bg-gradient-to-br from-purple-900/40 to-abyss/60 rounded-t-[1rem]"
          onClick={onPlay}
        >
          <span className="text-4xl opacity-40">
            {story.story_type === "historical" ? "🏛️" : "✨"}
          </span>
          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="w-12 h-12 rounded-full bg-black/50 backdrop-blur-sm
                            flex items-center justify-center text-white
                            shadow-[0_0_20px_rgba(0,0,0,0.3)]">
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 ml-0.5"><path d="M6 4l10 6-10 6z" /></svg>
            </div>
          </div>
          {cachedOffline && (
            <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded-full
                            bg-purple-900/80 text-purple-200 text-[9px] backdrop-blur-sm
                            border border-purple-500/20">
              Offline
            </div>
          )}
        </div>
      )}

      <div className="p-4 flex flex-col gap-2">
        {/* Title + overflow menu */}
        <div className="flex items-start gap-2">
          {isEditing ? (
            <div className="flex-1">
              <input
                type="text"
                value={editedTitle}
                onChange={(e) => setEditedTitle(e.target.value)}
                onBlur={handleSaveTitle}
                onKeyDown={handleKeyDown}
                autoFocus
                disabled={isSaving}
                className="text-base font-display text-glow bg-black/50 border border-purple-500/50
                           rounded px-2 py-1 text-white focus:outline-none focus:border-purple-400 w-full
                           disabled:opacity-50"
                placeholder="Story title"
              />
              <div className="text-[10px] text-starlight/40 mt-1">Enter to save, Esc to cancel</div>
            </div>
          ) : (
            <h3 className="flex-1 text-base font-display text-glow line-clamp-2 leading-snug">
              {story.title}
            </h3>
          )}

          {/* Overflow menu */}
          {!isEditing && (
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="w-8 h-8 shrink-0 rounded-full flex items-center justify-center
                         text-starlight/40 hover:text-starlight hover:bg-white/10
                         transition-all cursor-pointer text-sm"
              >
                ···
              </button>

              <AnimatePresence>
                {menuOpen && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9, y: -4 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9, y: -4 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 bottom-10 z-50 w-44 py-1
                             bg-abyss/95 border border-white/10 rounded-lg shadow-xl backdrop-blur-xl"
                  >
                    <button
                      onClick={handleCopyLink}
                      className="w-full px-4 py-2 text-left text-sm text-starlight/80 hover:bg-white/10 transition-colors"
                    >
                      {copied ? "Copied!" : "Copy link"}
                    </button>
                    <a
                      href={story.audio_url}
                      download={`${story.title}.mp3`}
                      onClick={() => setMenuOpen(false)}
                      className="block px-4 py-2 text-sm text-starlight/80 hover:bg-white/10 transition-colors"
                    >
                      Download MP3
                    </a>
                    <button
                      onClick={() => { setIsEditing(true); setMenuOpen(false); }}
                      className="w-full px-4 py-2 text-left text-sm text-starlight/80 hover:bg-white/10 transition-colors"
                    >
                      Edit title
                    </button>
                    {hasNoIllustrations && (
                      <button
                        onClick={() => { setMenuOpen(false); setShowStylePicker("add"); }}
                        disabled={isRegenerating}
                        className="w-full px-4 py-2 text-left text-sm text-starlight/80 hover:bg-white/10 transition-colors disabled:opacity-50"
                      >
                        Add illustrations
                      </button>
                    )}
                    {hasMissingImages && (
                      <button
                        onClick={() => handleIllustrationAction("missing")}
                        disabled={isRegenerating}
                        className="w-full px-4 py-2 text-left text-sm text-starlight/80 hover:bg-white/10 transition-colors disabled:opacity-50"
                      >
                        {isRegenerating ? "Regenerating..." : "Regenerate missing images"}
                      </button>
                    )}
                    {hasIllustrations && (
                      <button
                        onClick={() => { setMenuOpen(false); setShowStylePicker("all"); }}
                        disabled={isRegenerating}
                        className="w-full px-4 py-2 text-left text-sm text-starlight/80 hover:bg-white/10 transition-colors disabled:opacity-50"
                      >
                        Regenerate all images
                      </button>
                    )}
                    <div className="border-t border-white/10 my-1" />
                    <button
                      onClick={handleDelete}
                      disabled={isDeleting}
                      className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-900/30 transition-colors disabled:opacity-50"
                    >
                      {isDeleting ? "Deleting..." : "Delete story"}
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>

        {/* Regeneration status */}
        {regenStatus && (
          <div className="text-[11px] text-purple-300/80 animate-pulse">
            {regenStatus}
          </div>
        )}

        {/* Metadata */}
        <div className="flex items-center gap-1.5 text-xs text-starlight/50">
          <span>{story.kid_name}, {story.kid_age}</span>
          <span>·</span>
          <span>{getTypeLabel()}</span>
          <span>·</span>
          <span>{formatDuration(story.duration_seconds)}</span>
          <span>·</span>
          <span>{formatDate(story.created_at)}</span>
        </div>
      </div>

      {/* Art style picker modal */}
      <AnimatePresence>
        {showStylePicker && (
          <ArtStylePickerModal
            currentStyle={showStylePicker === "all" ? story.art_style : undefined}
            onConfirm={(artStyle, customPrompt) => {
              if (showStylePicker === "add") {
                handleIllustrationAction("add", artStyle, customPrompt);
              } else {
                setShowConfirmRegenAll({ artStyle, customPrompt });
              }
              setShowStylePicker(null);
            }}
            onCancel={() => setShowStylePicker(null)}
          />
        )}
      </AnimatePresence>

      {/* Confirm regenerate all dialog */}
      <AnimatePresence>
        {showConfirmRegenAll && (
          <ConfirmDialog
            title="Regenerate all images?"
            message={`This will replace all ${story.scenes?.length ?? 0} existing images. This cannot be undone.`}
            confirmLabel="Regenerate all"
            onConfirm={() => {
              handleIllustrationAction("all", showConfirmRegenAll.artStyle, showConfirmRegenAll.customPrompt);
              setShowConfirmRegenAll(null);
            }}
            onCancel={() => setShowConfirmRegenAll(null)}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}
