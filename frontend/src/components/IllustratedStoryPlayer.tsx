import { useRef, useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { Scene } from "../types";
import { useFullscreen } from "../hooks/useFullscreen";

interface Props {
  audioUrl: string;
  scenes: Scene[];
  title: string;
  durationSeconds: number;
  transcript?: string;
  onCreateAnother: () => void;
  onBackToLibrary?: () => void;
}

const formatTime = (seconds: number) => {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
};

export default function IllustratedStoryPlayer({
  audioUrl,
  scenes,
  title,
  durationSeconds,
  transcript,
  onCreateAnother,
  onBackToLibrary,
}: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(durationSeconds);
  const [isSeeking, setIsSeeking] = useState(false);
  const [currentSceneIndex, setCurrentSceneIndex] = useState(0);
  const [showTranscript, setShowTranscript] = useState(false);
  const [pageDirection, setPageDirection] = useState<"forward" | "backward">("forward");
  const { isFullscreen, toggleFullscreen, isSupported: fullscreenSupported } = useFullscreen(containerRef);

  // Update current scene based on audio time
  useEffect(() => {
    if (!scenes || scenes.length === 0) return;

    const activeSceneIndex = scenes.findIndex(
      (s) => currentTime >= s.timestamp_start && currentTime < s.timestamp_end
    );

    if (activeSceneIndex !== -1 && activeSceneIndex !== currentSceneIndex) {
      setPageDirection(activeSceneIndex > currentSceneIndex ? "forward" : "backward");
      setCurrentSceneIndex(activeSceneIndex);
    }
  }, [currentTime, scenes, currentSceneIndex]);

  // Preload next scene image
  useEffect(() => {
    const nextScene = scenes[currentSceneIndex + 1];
    if (nextScene?.image_url) {
      const img = new Image();
      img.src = nextScene.image_url;
    }
  }, [currentSceneIndex, scenes]);

  const handleLoadedMetadata = () => {
    if (audioRef.current && audioRef.current.duration && isFinite(audioRef.current.duration)) {
      setDuration(audioRef.current.duration);
    }
  };

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch((err) => {
        console.error("Playback failed:", err);
        setIsPlaying(false);
      });
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const t = Number(e.target.value);
    if (audioRef.current) audioRef.current.currentTime = t;
    setCurrentTime(t);
  };

  const handleSeekStart = () => setIsSeeking(true);
  const handleSeekEnd = () => setIsSeeking(false);

  const handleTimeUpdate = () => {
    if (!isSeeking && audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const jumpToScene = (sceneIndex: number) => {
    if (audioRef.current && scenes[sceneIndex]) {
      audioRef.current.currentTime = scenes[sceneIndex].timestamp_start;
      setCurrentTime(scenes[sceneIndex].timestamp_start);
    }
  };

  const currentScene = scenes[currentSceneIndex];

  return (
    <div
      ref={containerRef}
      className={`max-w-5xl mx-auto space-y-4 sm:space-y-8 ${
        isFullscreen
          ? "flex flex-col h-screen bg-void p-2"
          : "px-2 py-2 sm:px-4 sm:py-8"
      }`}
    >
      {/* Title */}
      {!isFullscreen && (
        <motion.h1
          className="text-2xl sm:text-3xl md:text-4xl font-display text-glow text-center"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {title}
        </motion.h1>
      )}

      {/* Scene indicator */}
      {currentScene && (
        <motion.div
          className="text-center text-xs sm:text-sm text-starlight/60"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          Chapter {currentSceneIndex + 1} of {scenes.length}: {currentScene.beat_name}
        </motion.div>
      )}

      {/* Illustration with page turn animation */}
      <div
        className={`relative ${isFullscreen ? "flex-1 min-h-0" : ""}`}
        style={{ perspective: "2000px" }}
      >
        <AnimatePresence mode="wait">
          {currentScene?.image_url && (
            <motion.div
              key={currentSceneIndex}
              initial={{
                rotateY: pageDirection === "forward" ? -90 : 90,
                opacity: 0,
              }}
              animate={{
                rotateY: 0,
                opacity: 1,
              }}
              exit={{
                rotateY: pageDirection === "forward" ? 90 : -90,
                opacity: 0,
              }}
              transition={{
                duration: 0.6,
                ease: "easeInOut",
              }}
              className={`w-full rounded-lg overflow-hidden shadow-2xl ${
                isFullscreen
                  ? "h-full"
                  : "aspect-[3/4] sm:aspect-[4/3]"
              }`}
              style={{
                transformStyle: "preserve-3d",
                backfaceVisibility: "hidden",
              }}
            >
              <img
                src={currentScene.image_url}
                alt={currentScene.beat_name}
                className="w-full h-full object-cover"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Audio Controls */}
      <div className={`glass-card p-3 sm:p-6 space-y-3 sm:space-y-4 ${
        isFullscreen ? "" : "sm:relative"
      }`}>
        <audio
          ref={audioRef}
          src={audioUrl}
          onLoadedMetadata={handleLoadedMetadata}
          onTimeUpdate={handleTimeUpdate}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
        />

        {/* Seek bar with scene markers */}
        <div className="relative">
          <input
            type="range"
            min={0}
            max={duration}
            value={currentTime}
            onChange={handleSeek}
            onMouseDown={handleSeekStart}
            onMouseUp={handleSeekEnd}
            onTouchStart={handleSeekStart}
            onTouchEnd={handleSeekEnd}
            className="w-full h-2 bg-starlight/10 rounded-lg appearance-none cursor-pointer
                     [&::-webkit-slider-thumb]:appearance-none
                     [&::-webkit-slider-thumb]:w-5
                     [&::-webkit-slider-thumb]:h-5
                     [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:bg-purple-500
                     [&::-webkit-slider-thumb]:cursor-pointer
                     [&::-webkit-slider-thumb]:shadow-[0_0_8px_rgba(168,85,247,0.6)]
                     [&::-moz-range-thumb]:w-5
                     [&::-moz-range-thumb]:h-5
                     [&::-moz-range-thumb]:rounded-full
                     [&::-moz-range-thumb]:bg-purple-500
                     [&::-moz-range-thumb]:cursor-pointer
                     [&::-moz-range-thumb]:border-0"
            style={{
              background: `linear-gradient(to right, rgb(168 85 247) 0%, rgb(168 85 247) ${(currentTime / duration) * 100}%, rgba(255,255,255,0.1) ${(currentTime / duration) * 100}%, rgba(255,255,255,0.1) 100%)`,
            }}
          />

          {/* Scene markers */}
          {scenes.map((scene, i) => (
            <button
              key={i}
              onClick={() => jumpToScene(i)}
              className="absolute top-0 w-2 h-2 bg-purple-300 rounded-full hover:scale-150 transition-transform cursor-pointer"
              style={{
                left: `${(scene.timestamp_start / duration) * 100}%`,
                transform: "translate(-50%, -25%)",
              }}
              title={scene.beat_name}
            />
          ))}
        </div>

        {/* Play/pause, time, and fullscreen */}
        <div className="flex items-center justify-between">
          <button
            onClick={togglePlay}
            className="w-12 h-12 rounded-full bg-purple-500 hover:bg-purple-600
                     flex items-center justify-center text-white text-xl
                     shadow-[0_0_15px_rgba(168,85,247,0.4)] hover:shadow-[0_0_20px_rgba(168,85,247,0.6)]
                     transition-all cursor-pointer"
          >
            {isPlaying ? "⏸" : "▶"}
          </button>

          <div className="text-sm text-starlight/60 font-mono">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>

          {fullscreenSupported && (
            <button
              onClick={toggleFullscreen}
              className="w-10 h-10 rounded-full flex items-center justify-center
                       text-starlight/60 hover:text-starlight hover:bg-white/10
                       transition-all cursor-pointer text-lg"
              title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
            >
              {isFullscreen ? "⤓" : "⤢"}
            </button>
          )}
        </div>
      </div>

      {/* Transcript Toggle — hidden in fullscreen */}
      {!isFullscreen && transcript && (
        <div className="text-center">
          <button
            onClick={() => setShowTranscript(!showTranscript)}
            className="text-sm text-starlight/60 hover:text-starlight underline cursor-pointer"
          >
            {showTranscript ? "Hide" : "Show"} Transcript
          </button>
        </div>
      )}

      {/* Transcript with Illustrations */}
      {!isFullscreen && (
        <AnimatePresence>
          {showTranscript && transcript && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="glass-card p-4 sm:p-6 space-y-8 overflow-hidden"
            >
              {scenes.map((scene, i) => (
                <div key={i} className="space-y-3">
                  <h3 className="font-display text-lg text-glow">
                    Chapter {i + 1}: {scene.beat_name}
                  </h3>
                  {scene.image_url && (
                    <img
                      src={scene.image_url}
                      alt={scene.beat_name}
                      loading="lazy"
                      className="w-full max-w-md mx-auto rounded-lg shadow-lg"
                    />
                  )}
                  <p className="text-starlight/80 leading-relaxed">
                    {scene.text_excerpt}
                  </p>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      )}

      {/* Actions — hidden in fullscreen */}
      {!isFullscreen && (
        <div className="flex gap-4 justify-center pt-2 sm:pt-4">
          {onBackToLibrary && (
            <button
              onClick={onBackToLibrary}
              className="px-6 py-3 rounded-xl glass-card text-ethereal hover:text-white text-sm font-medium transition-all cursor-pointer"
            >
              📚 Library
            </button>
          )}
          <button
            onClick={onCreateAnother}
            className="btn-glow text-sm cursor-pointer"
          >
            ✨ Create Another Story
          </button>
        </div>
      )}
    </div>
  );
}
