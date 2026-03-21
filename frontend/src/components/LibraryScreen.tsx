import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { StoryMetadata, LibraryView } from "../types";
import { listStories, deleteStory, updateStoryTitle } from "../api/client";
import StoryCard from "./StoryCard";

interface Props {
  onClose: () => void;
  onPlayStory: (story: StoryMetadata) => void;
}

export default function LibraryScreen({ onClose, onPlayStory }: Props) {
  const [stories, setStories] = useState<StoryMetadata[]>([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<LibraryView>("grid");
  const [filterKid, setFilterKid] = useState<string>("");
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const loadStories = async (reset: boolean = false) => {
    setLoading(true);
    setError(null);
    
    try {
      const newOffset = reset ? 0 : offset;
      const response = await listStories(
        filterKid || undefined,
        limit,
        newOffset,
        "created_desc"
      );
      
      if (reset) {
        setStories(response.stories);
        setOffset(limit);
      } else {
        setStories([...stories, ...response.stories]);
        setOffset(offset + limit);
      }
      
      setTotal(response.total);
      setHasMore(response.has_more);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load stories");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStories(true);
  }, [filterKid]);

  const handleDelete = async (story: StoryMetadata) => {
    if (!confirm(`Delete "${story.title}"? This cannot be undone.`)) {
      return;
    }

    try {
      await deleteStory(story.short_id);
      setStories(stories.filter(s => s.short_id !== story.short_id));
      setTotal(total - 1);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete story");
    }
  };

  const handleUpdateTitle = async (story: StoryMetadata, newTitle: string) => {
    try {
      const updated = await updateStoryTitle(story.short_id, newTitle);
      setStories(stories.map(s => s.short_id === story.short_id ? updated : s));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update title");
    }
  };

  const uniqueKids = Array.from(new Set(stories.map(s => s.kid_name))).sort();

  return (
    <div className="min-h-screen w-full flex flex-col items-center justify-center px-4 py-12">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-6xl mb-8"
      >
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-4xl font-display text-glow">📚 Your Story Library</h1>
          <button
            onClick={onClose}
            className="px-4 py-2 glass-card text-starlight hover:text-glow transition-all"
          >
            ✕ Close
          </button>
        </div>

        {/* Filters & View Toggle */}
        <div className="flex flex-wrap gap-4 items-center">
          <select
            value={filterKid}
            onChange={(e) => setFilterKid(e.target.value)}
            className="px-4 py-2 bg-black/50 border border-purple-500/50 rounded 
                       text-purple-100 focus:outline-none focus:border-purple-400"
          >
            <option value="">All Kids</option>
            {uniqueKids.map(kid => (
              <option key={kid} value={kid}>{kid}</option>
            ))}
          </select>

          <div className="flex gap-2">
            <button
              onClick={() => setView("grid")}
              className={`px-3 py-2 rounded text-sm transition-all ${
                view === "grid"
                  ? "bg-purple-600 text-white"
                  : "bg-black/30 text-purple-300 border border-purple-500/30"
              }`}
            >
              Grid
            </button>
            <button
              onClick={() => setView("grouped")}
              className={`px-3 py-2 rounded text-sm transition-all ${
                view === "grouped"
                  ? "bg-purple-600 text-white"
                  : "bg-black/30 text-purple-300 border border-purple-500/30"
              }`}
            >
              By Kid
            </button>
            <button
              onClick={() => setView("timeline")}
              className={`px-3 py-2 rounded text-sm transition-all ${
                view === "timeline"
                  ? "bg-purple-600 text-white"
                  : "bg-black/30 text-purple-300 border border-purple-500/30"
              }`}
            >
              📅 Timeline
            </button>
          </div>

          <div className="ml-auto text-sm text-starlight/60">
            {total} {total === 1 ? "story" : "stories"}
          </div>
        </div>
      </motion.div>

      {/* Content */}
      <div className="w-full max-w-6xl">
        {loading && stories.length === 0 ? (
          <div className="text-center text-starlight/60 py-20">
            Loading stories...
          </div>
        ) : error ? (
          <div className="text-center text-red-400 py-20">
            {error}
          </div>
        ) : stories.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-20"
          >
            <div className="text-6xl mb-4">📚</div>
            <h2 className="text-2xl font-display text-glow mb-2">No stories yet!</h2>
            <p className="text-starlight/60 mb-6">
              You haven't created any stories yet.
            </p>
            <button
              onClick={onClose}
              className="btn-glow"
            >
              Create Your First Story
            </button>
          </motion.div>
        ) : view === "grid" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <AnimatePresence>
              {stories.map((story) => (
                <StoryCard
                  key={story.short_id}
                  story={story}
                  onPlay={() => onPlayStory(story)}
                  onDelete={() => handleDelete(story)}
                  onUpdateTitle={(newTitle) => handleUpdateTitle(story, newTitle)}
                />
              ))}
            </AnimatePresence>
          </div>
        ) : view === "grouped" ? (
          <div className="space-y-6">
            {uniqueKids.map(kidName => {
              const kidStories = stories.filter(s => s.kid_name === kidName);
              return (
                <div key={kidName}>
                  <h2 className="text-2xl font-display text-glow mb-4">
                    {kidName} ({kidStories.length})
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {kidStories.map(story => (
                      <StoryCard
                        key={story.short_id}
                        story={story}
                        onPlay={() => onPlayStory(story)}
                        onDelete={() => handleDelete(story)}
                        onUpdateTitle={(newTitle) => handleUpdateTitle(story, newTitle)}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="space-y-6">
            {/* Timeline View - Group by date */}
            {(() => {
              const today: StoryMetadata[] = [];
              const yesterday: StoryMetadata[] = [];
              const thisWeek: StoryMetadata[] = [];
              const older: StoryMetadata[] = [];

              stories.forEach(story => {
                const date = new Date(story.created_at);
                const now = new Date();
                const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

                if (diffDays === 0) today.push(story);
                else if (diffDays === 1) yesterday.push(story);
                else if (diffDays < 7) thisWeek.push(story);
                else older.push(story);
              });

              return (
                <>
                  {today.length > 0 && (
                    <div>
                      <h2 className="text-2xl font-display text-glow mb-4">Today ({today.length})</h2>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {today.map(story => (
                          <StoryCard
                            key={story.short_id}
                            story={story}
                            onPlay={() => onPlayStory(story)}
                            onDelete={() => handleDelete(story)}
                            onUpdateTitle={(newTitle) => handleUpdateTitle(story, newTitle)}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                  {yesterday.length > 0 && (
                    <div>
                      <h2 className="text-2xl font-display text-glow mb-4">Yesterday ({yesterday.length})</h2>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {yesterday.map(story => (
                          <StoryCard
                            key={story.short_id}
                            story={story}
                            onPlay={() => onPlayStory(story)}
                            onDelete={() => handleDelete(story)}
                            onUpdateTitle={(newTitle) => handleUpdateTitle(story, newTitle)}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                  {thisWeek.length > 0 && (
                    <div>
                      <h2 className="text-2xl font-display text-glow mb-4">This Week ({thisWeek.length})</h2>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {thisWeek.map(story => (
                          <StoryCard
                            key={story.short_id}
                            story={story}
                            onPlay={() => onPlayStory(story)}
                            onDelete={() => handleDelete(story)}
                            onUpdateTitle={(newTitle) => handleUpdateTitle(story, newTitle)}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                  {older.length > 0 && (
                    <div>
                      <h2 className="text-2xl font-display text-glow mb-4">Older ({older.length})</h2>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {older.map(story => (
                          <StoryCard
                            key={story.short_id}
                            story={story}
                            onPlay={() => onPlayStory(story)}
                            onDelete={() => handleDelete(story)}
                            onUpdateTitle={(newTitle) => handleUpdateTitle(story, newTitle)}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                </>
              );
            })()}
          </div>
        )}

        {/* Load More */}
        {hasMore && !loading && (
          <div className="text-center mt-8">
            <button
              onClick={() => loadStories(false)}
              className="btn-glow"
            >
              Load More ({total - stories.length} more)
            </button>
          </div>
        )}

        {loading && stories.length > 0 && (
          <div className="text-center text-starlight/60 py-8">
            Loading more stories...
          </div>
        )}
      </div>
    </div>
  );
}
