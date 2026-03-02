import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface Props {
  isGenerating: boolean;
  currentStage: string;
  title: string;
  audioUrl: string;
  durationSeconds: number;
  onCreateAnother: () => void;
}

const STAGE_LABELS: Record<string, string> = {
  writing: "Weaving your tale...",
  splitting: "Giving voice to characters...",
  synthesizing: "Recording the narration...",
  stitching: "Binding the magic...",
};

const STAGES = Object.keys(STAGE_LABELS);

const formatTime = (seconds: number) => {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
};

export default function StoryScreen({
  isGenerating,
  currentStage,
  title,
  audioUrl,
  durationSeconds,
  onCreateAnother,
}: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const t = Number(e.target.value);
    if (audioRef.current) audioRef.current.currentTime = t;
    setCurrentTime(t);
  };

  const currentStageIndex = STAGES.indexOf(currentStage);
  const label = STAGE_LABELS[currentStage] || "Creating your story...";

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      <AnimatePresence mode="wait">
        {isGenerating ? (
          /* ─── Phase 1: Generation Animation ─── */
          <motion.div
            key="generating"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.5 }}
            className="flex flex-col items-center space-y-8"
          >
            {/* Pulsing Orb */}
            <motion.div
              className="w-32 h-32 rounded-full"
              style={{
                background:
                  "radial-gradient(circle, #a78bfa 0%, #7c3aed 50%, #4c1d95 100%)",
                boxShadow:
                  "0 0 40px rgba(124, 58, 237, 0.6), 0 0 80px rgba(124, 58, 237, 0.3), 0 0 120px rgba(124, 58, 237, 0.1)",
              }}
              animate={{
                scale: [1, 1.15, 1],
                opacity: [0.8, 1, 0.8],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
              }}
            />

            {/* Stage Label */}
            <AnimatePresence mode="wait">
              <motion.p
                key={currentStage}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="text-xl font-display text-glow text-ethereal"
              >
                {label}
              </motion.p>
            </AnimatePresence>

            {/* Progress Dots */}
            <div className="flex gap-3">
              {STAGES.map((stage, i) => {
                const isCompleted = i < currentStageIndex;
                const isCurrent = i === currentStageIndex;
                return (
                  <motion.div
                    key={stage}
                    className="w-3 h-3 rounded-full"
                    style={{
                      backgroundColor: isCompleted
                        ? "#7c3aed"
                        : isCurrent
                          ? "#a78bfa"
                          : "rgba(255, 255, 255, 0.15)",
                    }}
                    animate={
                      isCurrent
                        ? { scale: [1, 1.4, 1], opacity: [0.7, 1, 0.7] }
                        : {}
                    }
                    transition={
                      isCurrent
                        ? { duration: 1, repeat: Infinity, ease: "easeInOut" }
                        : {}
                    }
                  />
                );
              })}
            </div>

            {/* Subtitle */}
            <p className="text-sm text-starlight/40">
              This usually takes about a minute
            </p>
          </motion.div>
        ) : (
          audioUrl && (
            /* ─── Phase 2: Audio Player ─── */
            <motion.div
              key="player"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, ease: "easeOut" }}
              className="flex flex-col items-center space-y-8 w-full max-w-md"
            >
              {/* Story Title */}
              <h2 className="text-3xl md:text-4xl font-display text-glow text-center leading-snug">
                {title}
              </h2>

              {/* Player Card */}
              <div className="glass-card w-full p-6 space-y-6">
                {/* Seek Bar */}
                <input
                  type="range"
                  min={0}
                  max={durationSeconds}
                  value={currentTime}
                  onChange={handleSeek}
                  className="w-full h-2 rounded-full appearance-none cursor-pointer
                    bg-white/10
                    [&::-webkit-slider-thumb]:appearance-none
                    [&::-webkit-slider-thumb]:w-4
                    [&::-webkit-slider-thumb]:h-4
                    [&::-webkit-slider-thumb]:rounded-full
                    [&::-webkit-slider-thumb]:bg-mystic
                    [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(124,58,237,0.6)]
                    [&::-webkit-slider-runnable-track]:rounded-full
                    [&::-moz-range-thumb]:w-4
                    [&::-moz-range-thumb]:h-4
                    [&::-moz-range-thumb]:rounded-full
                    [&::-moz-range-thumb]:bg-mystic
                    [&::-moz-range-thumb]:border-none
                    [&::-moz-range-thumb]:shadow-[0_0_10px_rgba(124,58,237,0.6)]
                    accent-mystic"
                />

                {/* Time Display */}
                <div className="flex justify-between text-sm text-starlight/40">
                  <span>{formatTime(currentTime)}</span>
                  <span>{formatTime(durationSeconds)}</span>
                </div>

                {/* Play/Pause Button */}
                <div className="flex justify-center">
                  <motion.button
                    onClick={togglePlay}
                    whileTap={{ scale: 0.9 }}
                    whileHover={{
                      boxShadow:
                        "0 0 30px rgba(124, 58, 237, 0.6), 0 0 60px rgba(124, 58, 237, 0.3)",
                    }}
                    className="w-20 h-20 rounded-full flex items-center justify-center text-3xl text-white cursor-pointer"
                    style={{
                      background:
                        "linear-gradient(135deg, #7c3aed, #6d28d9)",
                      boxShadow:
                        "0 0 20px rgba(124, 58, 237, 0.4), 0 0 40px rgba(124, 58, 237, 0.15)",
                    }}
                  >
                    {isPlaying ? "⏸" : "▶"}
                  </motion.button>
                </div>

                {/* Hidden Audio Element */}
                <audio
                  ref={audioRef}
                  src={audioUrl}
                  onTimeUpdate={() =>
                    setCurrentTime(audioRef.current?.currentTime || 0)
                  }
                  onEnded={() => setIsPlaying(false)}
                />
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-4 w-full">
                <a
                  href={audioUrl}
                  download
                  className="glass-card px-6 py-3 text-center font-semibold text-starlight transition-all hover:text-glow"
                >
                  Download MP3
                </a>
                <button
                  onClick={onCreateAnother}
                  className="btn-glow flex-1 text-center"
                >
                  Create Another Story
                </button>
              </div>
            </motion.div>
          )
        )}
      </AnimatePresence>
    </div>
  );
}
