import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { fetchArtStyles } from "../api/client";
import type { ArtStyle } from "../types";

interface Props {
  selectedStyle: string | null;
  onSelect: (styleId: string | null) => void;
  customPrompt?: string;
  onCustomPromptChange?: (prompt: string) => void;
}

export default function ArtStyleSelector({
  selectedStyle,
  onSelect,
  customPrompt = "",
  onCustomPromptChange,
}: Props) {
  const [styles, setStyles] = useState<ArtStyle[]>([]);
  const [loading, setLoading] = useState(true);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    fetchArtStyles()
      .then((data) => {
        setStyles(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load art styles:", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="glass-card p-4 text-center">
        <div className="text-starlight/60">Loading art styles...</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Collapsible header */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full glass-card p-4 flex items-center justify-between hover:shadow-[0_0_20px_rgba(34,197,94,0.3)] transition-all"
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">🎨</span>
          <div className="text-left">
            <h3 className="font-display text-lg text-glow">
              Add Illustrations (Optional)
            </h3>
            <p className="text-sm text-starlight/60">
              {selectedStyle
                ? styles.find((s) => s.id === selectedStyle)?.name || "Custom style selected"
                : "Choose an art style for your story"}
            </p>
          </div>
        </div>
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.3 }}
          className="text-starlight/60"
        >
          ▼
        </motion.div>
      </button>

      {/* Expandable content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="glass-card p-6 space-y-4">
              {/* Skip illustrations button */}
              <motion.button
                type="button"
                onClick={() => onSelect(null)}
                className={`w-full p-4 rounded-lg border-2 transition-all ${
                  selectedStyle === null
                    ? "border-mystic bg-mystic/10 shadow-[0_0_15px_rgba(34,197,94,0.4)]"
                    : "border-starlight/20 hover:border-starlight/40"
                }`}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <div className="text-left">
                  <div className="font-semibold text-starlight">
                    No Illustrations
                  </div>
                  <div className="text-sm text-starlight/60">
                    Just the audio story (faster generation)
                  </div>
                </div>
              </motion.button>

              {/* Art style grid */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {styles
                  .filter((style) => style.id !== "custom")
                  .map((style) => (
                    <motion.button
                      type="button"
                      key={style.id}
                      onClick={() => onSelect(style.id)}
                      className={`p-4 rounded-lg border-2 transition-all text-left ${
                        selectedStyle === style.id
                          ? "border-mystic bg-mystic/10 shadow-[0_0_15px_rgba(34,197,94,0.4)]"
                          : "border-starlight/20 hover:border-starlight/40"
                      }`}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                    >
                      <div className="font-semibold text-starlight mb-1">
                        {style.name}
                      </div>
                      <div className="text-xs text-starlight/60">
                        {style.description}
                      </div>
                      {selectedStyle === style.id && (
                        <div className="mt-2 text-ethereal text-sm">✓ Selected</div>
                      )}
                    </motion.button>
                  ))}
              </div>

              {/* Custom style option */}
              <div>
                <motion.button
                  type="button"
                  onClick={() => onSelect("custom")}
                  className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                    selectedStyle === "custom"
                      ? "border-mystic bg-mystic/10"
                      : "border-starlight/20 hover:border-starlight/40"
                  }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="font-semibold text-starlight mb-1">
                    Custom Style
                  </div>
                  <div className="text-xs text-starlight/60">
                    Describe your own art style
                  </div>
                </motion.button>

                {selectedStyle === "custom" && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    className="mt-3"
                  >
                    <textarea
                      value={customPrompt}
                      onChange={(e) => onCustomPromptChange?.(e.target.value)}
                      placeholder="Example: oil painting style, impressionist, vibrant colors..."
                      className="w-full px-4 py-3 bg-starlight/5 border border-starlight/20 rounded-lg
                               text-starlight placeholder-starlight/40 focus:outline-none
                               focus:border-mystic focus:ring-2 focus:ring-mystic/20
                               resize-none"
                      rows={3}
                      maxLength={200}
                    />
                    <div className="text-xs text-starlight/40 mt-1 text-right">
                      {customPrompt.length}/200
                    </div>
                  </motion.div>
                )}
              </div>

              {/* Info text */}
              <div className="text-xs text-starlight/50 text-center pt-2">
                Illustrations add ~30 seconds to generation time
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
