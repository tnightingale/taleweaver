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
  const [controlsVisible, setControlsVisible] = useState(true);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
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

  // Auto-hide controls in fullscreen after 3s of inactivity
  const resetHideTimer = () => {
    setControlsVisible(true);
    if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    if (isFullscreen) {
      hideTimerRef.current = setTimeout(() => setControlsVisible(false), 3000);
    }
  };

  useEffect(() => {
    if (isFullscreen) {
      setControlsVisible(true);
      hideTimerRef.current = setTimeout(() => setControlsVisible(false), 3000);
    } else {
      setControlsVisible(true);
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    }
    return () => { if (hideTimerRef.current) clearTimeout(hideTimerRef.current); };
  }, [isFullscreen]);

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

  const restartFromBeginning = () => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = 0;
    setCurrentTime(0);
    audioRef.current.play().catch(() => {});
  };

  const jumpToScene = (sceneIndex: number) => {
    if (audioRef.current && scenes[sceneIndex]) {
      audioRef.current.currentTime = scenes[sceneIndex].timestamp_start;
      setCurrentTime(scenes[sceneIndex].timestamp_start);
    }
  };

  const currentScene = scenes[currentSceneIndex];

  // Shared seek bar classes
  const seekBarClass = `w-full h-1.5 sm:h-2 bg-starlight/10 rounded-lg appearance-none cursor-pointer
    [&::-webkit-slider-thumb]:appearance-none
    [&::-webkit-slider-thumb]:w-4
    [&::-webkit-slider-thumb]:h-4
    [&::-webkit-slider-thumb]:rounded-full
    [&::-webkit-slider-thumb]:bg-purple-500
    [&::-webkit-slider-thumb]:cursor-pointer
    [&::-webkit-slider-thumb]:shadow-[0_0_8px_rgba(168,85,247,0.6)]
    [&::-moz-range-thumb]:w-4
    [&::-moz-range-thumb]:h-4
    [&::-moz-range-thumb]:rounded-full
    [&::-moz-range-thumb]:bg-purple-500
    [&::-moz-range-thumb]:cursor-pointer
    [&::-moz-range-thumb]:border-0`;

  const seekBarStyle = {
    background: `linear-gradient(to right, rgb(168 85 247) 0%, rgb(168 85 247) ${(currentTime / duration) * 100}%, rgba(255,255,255,0.1) ${(currentTime / duration) * 100}%, rgba(255,255,255,0.1) 100%)`,
  };

  return (
    <div
      ref={containerRef}
      className={`max-w-5xl mx-auto ${
        isFullscreen
          ? "relative h-screen bg-void overflow-hidden"
          : "sm:px-4 sm:py-8 sm:space-y-8 flex flex-col sm:block h-[100dvh] sm:h-auto"
      }`}
      onClick={isFullscreen ? resetHideTimer : undefined}
      onMouseMove={isFullscreen ? resetHideTimer : undefined}
    >
      <audio
        ref={audioRef}
        src={audioUrl}
        onLoadedMetadata={handleLoadedMetadata}
        onTimeUpdate={handleTimeUpdate}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => setIsPlaying(false)}
      />

      {/* Title — hidden on mobile, visible on sm+ (desktop) */}
      {!isFullscreen && (
        <motion.h1
          className="hidden sm:block text-3xl md:text-4xl font-display text-glow text-center"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {title}
        </motion.h1>
      )}

      {/* ── Image Area ── */}
      <div
        className={`relative cursor-pointer ${
          isFullscreen ? "w-full h-full" : "flex-1 sm:flex-none"
        }`}
        style={isFullscreen ? undefined : { perspective: "2000px" }}
        onClick={(e) => {
          // Don't toggle play if clicking on a control (button, input, etc.)
          if ((e.target as HTMLElement).closest("button, input")) return;
          togglePlay();
          if (isFullscreen) resetHideTimer();
        }}
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={currentSceneIndex}
            initial={isFullscreen ? { opacity: 0 } : {
              rotateY: pageDirection === "forward" ? -90 : 90,
              opacity: 0,
            }}
            animate={isFullscreen ? { opacity: 1 } : {
              rotateY: 0,
              opacity: 1,
            }}
            exit={isFullscreen ? { opacity: 0 } : {
              rotateY: pageDirection === "forward" ? 90 : -90,
              opacity: 0,
            }}
            transition={{
              duration: isFullscreen ? 0.3 : 0.6,
              ease: "easeInOut",
            }}
            className={`w-full overflow-hidden ${
              isFullscreen
                ? "h-full"
                : "h-full max-h-[75dvh] sm:max-h-none sm:h-auto sm:aspect-[4/3] rounded-none sm:rounded-lg shadow-2xl"
            }`}
            style={isFullscreen ? undefined : {
              transformStyle: "preserve-3d",
              backfaceVisibility: "hidden",
            }}
          >
            {/* Play overlay — visible when paused */}
            {!isPlaying && (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/20 transition-opacity">
                <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-black/50 backdrop-blur-sm
                                flex items-center justify-center text-white
                                shadow-[0_0_30px_rgba(0,0,0,0.3)]">
                  <svg viewBox="0 0 20 20" fill="currentColor" className="w-7 h-7 sm:w-9 sm:h-9 ml-1">
                    <path d="M6 4l10 6-10 6z" />
                  </svg>
                </div>
              </div>
            )}
            {currentScene?.image_url ? (
              <img
                src={currentScene.image_url}
                alt={currentScene.beat_name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full bg-gradient-to-br from-purple-900/40 to-abyss/80" />
            )}
          </motion.div>
        </AnimatePresence>

        {/* Floating chapter indicator — overlays top of image */}
        {currentScene && (
          <AnimatePresence mode="wait">
            <motion.div
              key={currentSceneIndex}
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className={`absolute top-0 left-0 right-0 z-10 px-4 pb-6
                bg-gradient-to-b from-black/60 via-black/30 to-transparent
                ${isFullscreen && !controlsVisible ? "opacity-0" : ""}
                transition-opacity duration-300`}
              style={{ paddingTop: 'calc(env(safe-area-inset-top, 0px) + 0.75rem)' }}
            >
              <p className="text-xs sm:text-sm text-white/80 text-center drop-shadow-lg">
                Chapter {currentSceneIndex + 1} of {scenes.length}: {currentScene.beat_name}
              </p>
            </motion.div>
          </AnimatePresence>
        )}
      </div>

      {/* ── Pinned Audio Controls (mobile) / Normal card (desktop) ── */}
      <div
        className={`z-20 ${
          isFullscreen
            ? `absolute bottom-0 left-0 right-0 transition-opacity duration-300
               ${controlsVisible ? "opacity-100" : "opacity-0 pointer-events-none"}
               bg-gradient-to-t from-black/80 via-black/50 to-transparent pt-8 pb-4 px-4`
            : `fixed left-0 right-0 sm:relative sm:static
               bottom-[calc(3rem+env(safe-area-inset-bottom))] sm:bottom-auto
               glass-card sm:rounded-2xl rounded-none
               border-t border-white/10 sm:border
               backdrop-blur-xl
               px-4 py-2.5 sm:p-6 sm:pb-6`
        }`}
        style={!isFullscreen ? { WebkitBackdropFilter: "blur(20px)" } : undefined}
      >
        {/* Mobile: compact single row. Desktop: stacked layout */}
        <div className="sm:hidden flex items-center gap-2">
          <button
            onClick={restartFromBeginning}
            className="w-8 h-8 shrink-0 rounded-full flex items-center justify-center
                     text-purple-300/60 hover:text-purple-200 hover:bg-purple-500/20
                     transition-all cursor-pointer"
            title="Start from beginning"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <rect x="2" y="4" width="2.5" height="12" rx="0.5" />
              <path d="M7 10l8-6v12z" />
            </svg>
          </button>
          <button
            onClick={togglePlay}
            className="w-10 h-10 shrink-0 rounded-full bg-purple-500/90 hover:bg-purple-500
                     flex items-center justify-center text-white
                     shadow-[0_0_12px_rgba(168,85,247,0.3)]
                     transition-all cursor-pointer"
          >
            {isPlaying ? (
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <rect x="5" y="4" width="3" height="12" rx="0.5" />
                <rect x="12" y="4" width="3" height="12" rx="0.5" />
              </svg>
            ) : (
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 ml-0.5">
                <path d="M6 4l10 6-10 6z" />
              </svg>
            )}
          </button>

          <div className="flex-1 relative">
            <input
              type="range"
              min={0}
              max={duration}
              value={currentTime}
              onChange={handleSeek}
              onTouchStart={handleSeekStart}
              onTouchEnd={handleSeekEnd}
              className={seekBarClass}
              style={seekBarStyle}
            />
            {/* Scene markers — calc accounts for range thumb radius (8px) so dots align with track */}
            {scenes.map((scene, i) => (
              <button
                key={i}
                onClick={() => jumpToScene(i)}
                className="absolute w-1.5 h-1.5 bg-purple-300 rounded-full cursor-pointer"
                style={{
                  left: `calc(8px + (100% - 16px) * ${scene.timestamp_start / duration})`,
                  top: 'calc(100% + 4px)',
                  transform: "translate(-50%, 0)",
                }}
              />
            ))}
          </div>

          <span className="text-[10px] text-starlight/50 font-mono shrink-0 w-[4.5rem] text-right">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>

          {fullscreenSupported && (
            <button
              onClick={toggleFullscreen}
              className="w-8 h-8 shrink-0 rounded-full flex items-center justify-center
                       text-purple-300/60 hover:text-purple-200 hover:bg-purple-500/20
                       transition-all cursor-pointer"
            >
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-4 h-4">
                {isFullscreen ? (
                  <>
                    <polyline points="7,3 7,7 3,7" />
                    <polyline points="13,17 13,13 17,13" />
                    <polyline points="17,7 13,7 13,3" />
                    <polyline points="3,13 7,13 7,17" />
                  </>
                ) : (
                  <>
                    <polyline points="3,7 3,3 7,3" />
                    <polyline points="17,13 17,17 13,17" />
                    <polyline points="13,3 17,3 17,7" />
                    <polyline points="7,17 3,17 3,13" />
                  </>
                )}
              </svg>
            </button>
          )}
        </div>

        {/* Desktop: full layout (hidden on mobile) */}
        <div className="hidden sm:block space-y-4">
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
              className={seekBarClass}
              style={seekBarStyle}
            />
            {/* Scene markers — calc accounts for range thumb radius (8px) */}
            {scenes.map((scene, i) => (
              <button
                key={i}
                onClick={() => jumpToScene(i)}
                className="absolute top-0 w-2 h-2 bg-purple-300 rounded-full hover:scale-150 transition-transform cursor-pointer"
                style={{
                  left: `calc(8px + (100% - 16px) * ${scene.timestamp_start / duration})`,
                  transform: "translate(-50%, -25%)",
                }}
                title={scene.beat_name}
              />
            ))}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={restartFromBeginning}
                className="w-10 h-10 rounded-full flex items-center justify-center
                         text-purple-300/60 hover:text-purple-200 hover:bg-purple-500/20
                         transition-all cursor-pointer"
                title="Start from beginning"
              >
                <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                  <rect x="2" y="4" width="2.5" height="12" rx="0.5" />
                  <path d="M7 10l8-6v12z" />
                </svg>
              </button>
              <button
                onClick={togglePlay}
                className="w-12 h-12 rounded-full bg-purple-500/90 hover:bg-purple-500
                         flex items-center justify-center text-white
                         shadow-[0_0_15px_rgba(168,85,247,0.3)] hover:shadow-[0_0_20px_rgba(168,85,247,0.5)]
                         transition-all cursor-pointer"
              >
                {isPlaying ? (
                  <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                    <rect x="5" y="4" width="3" height="12" rx="0.5" />
                    <rect x="12" y="4" width="3" height="12" rx="0.5" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 ml-0.5">
                    <path d="M6 4l10 6-10 6z" />
                  </svg>
                )}
              </button>
            </div>

            <div className="text-sm text-starlight/60 font-mono">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>

            {fullscreenSupported && (
              <button
                onClick={toggleFullscreen}
                className="w-10 h-10 rounded-full flex items-center justify-center
                         text-purple-300/60 hover:text-purple-200 hover:bg-purple-500/20
                         transition-all cursor-pointer"
                title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
              >
                <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5">
                  {isFullscreen ? (
                    <>
                      <polyline points="7,3 7,7 3,7" />
                      <polyline points="13,17 13,13 17,13" />
                      <polyline points="17,7 13,7 13,3" />
                      <polyline points="3,13 7,13 7,17" />
                    </>
                  ) : (
                    <>
                      <polyline points="3,7 3,3 7,3" />
                      <polyline points="17,13 17,17 13,17" />
                      <polyline points="13,3 17,3 17,7" />
                      <polyline points="7,17 3,17 3,13" />
                    </>
                  )}
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Mobile: nav buttons pinned below the player */}
      {!isFullscreen && (
        <div className="sm:hidden fixed bottom-0 left-0 right-0 z-10
                        flex items-center justify-center gap-2
                        py-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))]
                        bg-void/90 backdrop-blur-sm border-t border-white/5">
          {onBackToLibrary && (
            <button
              onClick={onBackToLibrary}
              className="px-4 py-1.5 rounded-full text-[11px] font-medium
                       bg-white/5 border border-purple-500/20 text-purple-200
                       hover:bg-purple-500/20 transition-all cursor-pointer"
            >
              Library
            </button>
          )}
          <button
            onClick={onCreateAnother}
            className="px-4 py-1.5 rounded-full text-[11px] font-medium
                     bg-purple-500/20 border border-purple-500/30 text-purple-200
                     hover:bg-purple-500/30 transition-all cursor-pointer"
          >
            New Story
          </button>
        </div>
      )}

      {/* Transcript Toggle — desktop only (mobile has no room) */}
      {!isFullscreen && transcript && (
        <div className="hidden sm:block text-center">
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
              className="glass-card p-4 sm:p-6 space-y-8 overflow-hidden mx-4 sm:mx-0"
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

      {/* Actions — desktop only (mobile has these in the player bar) */}
      {!isFullscreen && (
        <div className="hidden sm:flex gap-4 justify-center pt-4">
          {onBackToLibrary && (
            <button
              onClick={onBackToLibrary}
              className="px-6 py-3 rounded-xl glass-card text-ethereal hover:text-white text-sm font-medium transition-all cursor-pointer"
            >
              Library
            </button>
          )}
          <button
            onClick={onCreateAnother}
            className="btn-glow text-sm cursor-pointer"
          >
            Create Another Story
          </button>
        </div>
      )}
    </div>
  );
}
