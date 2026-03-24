import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { fetchArtStyles } from "../api/client";
import type { ArtStyle } from "../types";

interface Props {
  currentStyle?: string;
  onConfirm: (artStyle: string, customPrompt?: string) => void;
  onCancel: () => void;
}

export default function ArtStylePickerModal({
  currentStyle,
  onConfirm,
  onCancel,
}: Props) {
  const [styles, setStyles] = useState<ArtStyle[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(currentStyle ?? null);
  const [customPrompt, setCustomPrompt] = useState("");

  useEffect(() => {
    fetchArtStyles()
      .then((data) => {
        setStyles(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const canConfirm = selected && (selected !== "custom" || customPrompt.trim().length > 0);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onCancel}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        transition={{ duration: 0.15 }}
        className="glass-card p-6 max-w-lg w-full space-y-5 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-display text-glow">Choose an art style</h3>

        {loading ? (
          <div className="text-center text-starlight/60 py-8">Loading styles...</div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3">
              {styles
                .filter((s) => s.id !== "custom")
                .map((style) => (
                  <button
                    key={style.id}
                    onClick={() => setSelected(style.id)}
                    className={`p-3 rounded-lg border-2 text-left transition-all cursor-pointer ${
                      selected === style.id
                        ? "border-purple-500 bg-purple-500/10 shadow-[0_0_15px_rgba(124,58,237,0.4)]"
                        : "border-starlight/20 hover:border-starlight/40"
                    }`}
                  >
                    <div className="font-semibold text-starlight text-sm">{style.name}</div>
                    <div className="text-xs text-starlight/60 mt-0.5">{style.description}</div>
                  </button>
                ))}
            </div>

            <button
              onClick={() => setSelected("custom")}
              className={`w-full p-3 rounded-lg border-2 text-left transition-all cursor-pointer ${
                selected === "custom"
                  ? "border-purple-500 bg-purple-500/10"
                  : "border-starlight/20 hover:border-starlight/40"
              }`}
            >
              <div className="font-semibold text-starlight text-sm">Custom Style</div>
              <div className="text-xs text-starlight/60">Describe your own art style</div>
            </button>

            {selected === "custom" && (
              <textarea
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="Example: oil painting style, impressionist, vibrant colors..."
                className="w-full px-4 py-3 bg-starlight/5 border border-starlight/20 rounded-lg
                         text-starlight placeholder-starlight/40 focus:outline-none
                         focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 resize-none text-sm"
                rows={3}
                maxLength={200}
              />
            )}
          </>
        )}

        <div className="flex gap-3 justify-end pt-2">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-lg text-sm text-starlight/60 hover:text-starlight
                     hover:bg-white/10 transition-all cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              if (selected) {
                onConfirm(selected, selected === "custom" ? customPrompt : undefined);
              }
            }}
            disabled={!canConfirm}
            className="px-4 py-2 rounded-lg text-sm font-semibold bg-purple-600 hover:bg-purple-500
                     text-white transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Confirm
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}
