import { useRef, useState, useEffect, type ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { Scene } from "../types";
import { regenerateIllustrations } from "../api/client";
import { useFullscreen } from "../hooks/useFullscreen";

interface Props {
  audioUrl: string;
  scenes: Scene[];
  title: string;
  shortId?: string;
  durationSeconds: number;
  transcript?: string;
  onCreateAnother: () => void;
  onBackToLibrary?: () => void;
  offlineStatus?: ReactNode;
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
  shortId,
  durationSeconds,
  transcript,
  onCreateAnother,
  onBackToLibrary,
  offlineStatus,
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
  const [isLandscape, setIsLandscape] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [regenStatus, setRegenStatus] = useState("");
  const menuRef = useRef<HTMLDivElement>(null);
  const { isFullscreen, toggleFullscreen, isSupported: fullscreenSupported } = useFullscreen(containerRef);

  const hasMissingImages = scenes?.some(s => !s.image_url);

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

  const handleRegenerate = async () => {
    if (!shortId) return;
    setIsRegenerating(true);
    setRegenStatus("Starting...");
    setMenuOpen(false);
    try {
      const result = await regenerateIllustrations(shortId);
      if (result.message) {
        setRegenStatus(result.message);
        setTimeout(() => { setIsRegenerating(false); setRegenStatus(""); }, 2000);
      } else {
        setRegenStatus(`Regenerating ${result.failed_count} images...`);
        setTimeout(() => { setIsRegenerating(false); setRegenStatus(""); }, 10000);
      }
    } catch (err) {
      setRegenStatus(err instanceof Error ? err.message : "Failed to regenerate");
      setTimeout(() => { setIsRegenerating(false); setRegenStatus(""); }, 3000);
    }
  };

  // Orientation detection
  useEffect(() => {
    const mql = window.matchMedia("(orientation: landscape)");
    setIsLandscape(mql.matches);
    const handler = (e: MediaQueryListEvent) => setIsLandscape(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

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

  // Auto-hide controls in landscape after 3s of inactivity
  const resetHideTimer = () => {
    setControlsVisible(true);
    if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    if (isLandscape) {
      hideTimerRef.current = setTimeout(() => setControlsVisible(false), 3000);
    }
  };

  useEffect(() => {
    if (isLandscape) {
      setControlsVisible(true);
      hideTimerRef.current = setTimeout(() => setControlsVisible(false), 3000);
    } else {
      setControlsVisible(true);
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    }
    return () => { if (hideTimerRef.current) clearTimeout(hideTimerRef.current); };
  }, [isLandscape]);

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

  // Shared seek bar with scene markers
  const seekBar = (
    <div className="flex-1 relative">
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
      {scenes.map((scene, i) => (
        <button
          key={i}
          onClick={() => jumpToScene(i)}
          className="absolute w-1.5 h-1.5 bg-purple-300 rounded-full cursor-pointer"
          style={{
            left: `calc(8px + (100% - 16px) * ${scene.timestamp_start / duration})`,
            top: "calc(100% + 4px)",
            transform: "translate(-50%, 0)",
          }}
        />
      ))}
    </div>
  );

  // Play/pause icon
  const playPauseIcon = isPlaying ? (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
      <rect x="5" y="4" width="3" height="12" rx="0.5" />
      <rect x="12" y="4" width="3" height="12" rx="0.5" />
    </svg>
  ) : (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 ml-0.5">
      <path d="M6 4l10 6-10 6z" />
    </svg>
  );

  // Restart icon
  const restartIcon = (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
      <rect x="2" y="4" width="2.5" height="12" rx="0.5" />
      <path d="M7 10l8-6v12z" />
    </svg>
  );

  // Fullscreen icon
  const fullscreenIcon = (expand: boolean) => (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5">
      {expand ? (
        <>
          <polyline points="3,7 3,3 7,3" />
          <polyline points="17,13 17,17 13,17" />
          <polyline points="13,3 17,3 17,7" />
          <polyline points="7,17 3,17 3,13" />
        </>
      ) : (
        <>
          <polyline points="7,3 7,7 3,7" />
          <polyline points="13,17 13,13 17,13" />
          <polyline points="17,7 13,7 13,3" />
          <polyline points="3,13 7,13 7,17" />
        </>
      )}
    </svg>
  );

  // Image with page-turn animation
  const imageArea = (landscape: boolean) => (
    <AnimatePresence mode="wait">
      <motion.div
        key={currentSceneIndex}
        initial={landscape ? { opacity: 0 } : {
          rotateY: pageDirection === "forward" ? -90 : 90,
          opacity: 0,
        }}
        animate={landscape ? { opacity: 1 } : {
          rotateY: 0,
          opacity: 1,
        }}
        exit={landscape ? { opacity: 0 } : {
          rotateY: pageDirection === "forward" ? 90 : -90,
          opacity: 0,
        }}
        transition={{
          duration: landscape ? 0.3 : 0.6,
          ease: "easeInOut",
        }}
        className={landscape
          ? "w-full h-full"
          : "w-full overflow-hidden sm:rounded-lg sm:shadow-2xl"
        }
        style={landscape ? undefined : {
          transformStyle: "preserve-3d",
          backfaceVisibility: "hidden",
        }}
      >
        {currentScene?.image_url ? (
          <img
            src={currentScene.image_url}
            alt={currentScene.beat_name}
            className={landscape
              ? "w-full h-full object-cover"
              : "w-full h-auto"
            }
          />
        ) : (
          <div className={`w-full bg-gradient-to-br from-purple-900/40 to-abyss/80 ${landscape ? "h-full" : "aspect-[4/3]"}`} />
        )}
      </motion.div>
    </AnimatePresence>
  );

  // Play overlay — visible when paused
  const playOverlay = !isPlaying && (
    <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/20 transition-opacity">
      <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-black/50 backdrop-blur-sm
                      flex items-center justify-center text-white
                      shadow-[0_0_30px_rgba(0,0,0,0.3)]">
        <svg viewBox="0 0 20 20" fill="currentColor" className="w-7 h-7 sm:w-9 sm:h-9 ml-1">
          <path d="M6 4l10 6-10 6z" />
        </svg>
      </div>
    </div>
  );

  const audioElement = (
    <audio
      ref={audioRef}
      src={audioUrl}
      onLoadedMetadata={handleLoadedMetadata}
      onTimeUpdate={handleTimeUpdate}
      onPlay={() => setIsPlaying(true)}
      onPause={() => setIsPlaying(false)}
      onEnded={() => setIsPlaying(false)}
    />
  );

  // ═══════════════════════════════════════════
  // LANDSCAPE LAYOUT — Immersive TV-player style
  // ═══════════════════════════════════════════
  if (isLandscape) {
    return (
      <div
        ref={containerRef}
        className="fixed inset-0 bg-black z-50"
        onClick={resetHideTimer}
        onMouseMove={resetHideTimer}
      >
        {audioElement}

        {/* Full-viewport image */}
        <div
          className="w-full h-full cursor-pointer"
          onClick={(e) => {
            if ((e.target as HTMLElement).closest("button, input")) return;
            togglePlay();
            resetHideTimer();
          }}
        >
          {imageArea(true)}
          {playOverlay}
          {/* Offline status — top-right of illustration */}
          {offlineStatus && (
            <div className="absolute top-3 right-3 z-10">{offlineStatus}</div>
          )}
        </div>

        {/* Floating chapter title — top overlay */}
        {currentScene && (
          <div
            className={`absolute top-0 left-0 right-0 z-10 px-4 pb-6
              bg-gradient-to-b from-black/60 via-black/30 to-transparent
              transition-opacity duration-300
              ${controlsVisible ? "opacity-100" : "opacity-0 pointer-events-none"}`}
            style={{ paddingTop: "calc(env(safe-area-inset-top, 0px) + 0.75rem)" }}
          >
            <AnimatePresence mode="wait">
              <motion.p
                key={currentSceneIndex}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3 }}
                className="text-xs sm:text-sm text-white/80 text-center drop-shadow-lg"
              >
                Chapter {currentSceneIndex + 1} of {scenes.length}: {currentScene.beat_name}
              </motion.p>
            </AnimatePresence>
          </div>
        )}

        {/* Floating controls — bottom overlay */}
        <div
          className={`absolute bottom-0 left-0 right-0 z-20 transition-opacity duration-300
            ${controlsVisible ? "opacity-100" : "opacity-0 pointer-events-none"}
            bg-gradient-to-t from-black/70 via-black/40 to-transparent pt-8 pb-4 px-4`}
          style={{ paddingBottom: "calc(env(safe-area-inset-bottom, 0px) + 1rem)" }}
        >
          <div className="flex items-center gap-3 max-w-3xl mx-auto">
            <button
              onClick={restartFromBeginning}
              className="w-9 h-9 shrink-0 rounded-full flex items-center justify-center
                       text-white/60 hover:text-white hover:bg-white/10
                       transition-all cursor-pointer"
              title="Start from beginning"
            >
              {restartIcon}
            </button>
            <button
              onClick={togglePlay}
              className="w-12 h-12 shrink-0 rounded-full bg-purple-500/90 hover:bg-purple-500
                       flex items-center justify-center text-white
                       shadow-[0_0_12px_rgba(168,85,247,0.3)]
                       transition-all cursor-pointer"
            >
              {playPauseIcon}
            </button>

            {seekBar}

            <span className="text-xs text-white/50 font-mono shrink-0">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>

            {fullscreenSupported && (
              <button
                onClick={toggleFullscreen}
                className="w-9 h-9 shrink-0 rounded-full flex items-center justify-center
                         text-white/60 hover:text-white hover:bg-white/10
                         transition-all cursor-pointer"
                title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
              >
                {fullscreenIcon(!isFullscreen)}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════
  // PORTRAIT LAYOUT — Natural document flow
  // ═══════════════════════════════════════════
  return (
    <div
      ref={containerRef}
      className="max-w-5xl mx-auto px-0 sm:px-4 py-0 sm:py-8"
      style={{
        paddingTop: "env(safe-area-inset-top)",
        paddingBottom: "env(safe-area-inset-bottom)",
      }}
    >
      {audioElement}

      {/* Story title — desktop only */}
      <motion.h1
        className="hidden sm:block text-3xl md:text-4xl font-display text-glow text-center mb-8"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        {title}
      </motion.h1>

      {/* Chapter title — above image */}
      {currentScene && (
        <div className="text-center py-3 px-4">
          <AnimatePresence mode="wait">
            <motion.p
              key={currentSceneIndex}
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className="text-sm text-starlight/70 font-display"
            >
              Chapter {currentSceneIndex + 1} of {scenes.length}: {currentScene.beat_name}
            </motion.p>
          </AnimatePresence>
        </div>
      )}

      {/* Image — full width, natural aspect ratio */}
      <div
        className="w-full cursor-pointer relative"
        style={{ perspective: "2000px" }}
        onClick={(e) => {
          if ((e.target as HTMLElement).closest("button, input")) return;
          togglePlay();
        }}
      >
        {imageArea(false)}
        {playOverlay}
        {/* Offline status — top-right of illustration */}
        {offlineStatus && (
          <div className="absolute top-3 right-3 z-10">{offlineStatus}</div>
        )}
      </div>

      {/* Player controls — glass card */}
      <div
        className="glass-card mx-2 sm:mx-0 rounded-2xl border border-white/10 backdrop-blur-xl px-4 py-3 mt-3"
        style={{ WebkitBackdropFilter: "blur(20px)" }}
      >
        <div className="flex items-center gap-3">
          <button
            onClick={restartFromBeginning}
            className="w-9 h-9 shrink-0 rounded-full flex items-center justify-center
                     text-purple-300/60 hover:text-purple-200 hover:bg-purple-500/20
                     transition-all cursor-pointer"
            title="Start from beginning"
          >
            {restartIcon}
          </button>
          <button
            onClick={togglePlay}
            className="w-12 h-12 shrink-0 rounded-full bg-purple-500/90 hover:bg-purple-500
                     flex items-center justify-center text-white
                     shadow-[0_0_12px_rgba(168,85,247,0.3)]
                     transition-all cursor-pointer"
          >
            {playPauseIcon}
          </button>

          {seekBar}

          <span className="text-xs text-starlight/50 font-mono shrink-0">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>

          {fullscreenSupported && (
            <button
              onClick={toggleFullscreen}
              className="w-9 h-9 shrink-0 rounded-full flex items-center justify-center
                       text-purple-300/60 hover:text-purple-200 hover:bg-purple-500/20
                       transition-all cursor-pointer"
              title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
            >
              {fullscreenIcon(!isFullscreen)}
            </button>
          )}
        </div>
      </div>

      {/* Nav buttons */}
      <div className="flex items-center justify-center gap-3 py-3">
        {onBackToLibrary && (
          <button
            onClick={onBackToLibrary}
            className="flex items-center gap-1.5 px-5 py-2 rounded-full text-xs font-medium
                     bg-white/5 border border-purple-500/20 text-purple-200
                     hover:bg-purple-500/20 transition-all cursor-pointer"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
              <path d="M3 4h6v6H3V4zm0 8h6v4H3v-4zm8-8h6v4h-6V4zm0 6h6v6h-6v-6z"/>
            </svg>
            Library
          </button>
        )}
        <button
          onClick={onCreateAnother}
          className="flex items-center gap-1.5 px-5 py-2 rounded-full text-xs font-medium
                   bg-purple-500/20 border border-purple-500/30 text-purple-200
                   hover:bg-purple-500/30 transition-all cursor-pointer"
        >
          <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
            <path d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"/>
          </svg>
          New Story
        </button>
        {shortId && hasMissingImages && (
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="flex items-center justify-center w-9 h-9 rounded-full text-xs font-medium
                       bg-white/5 border border-purple-500/20 text-purple-200
                       hover:bg-purple-500/20 transition-all cursor-pointer"
              title="More options"
            >
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <circle cx="10" cy="4" r="1.5" />
                <circle cx="10" cy="10" r="1.5" />
                <circle cx="10" cy="16" r="1.5" />
              </svg>
            </button>
            <AnimatePresence>
              {menuOpen && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: -4 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: -4 }}
                  transition={{ duration: 0.15 }}
                  className="absolute bottom-full mb-2 right-0 min-w-[180px] rounded-xl overflow-hidden
                           bg-black/80 backdrop-blur-xl border border-white/10 shadow-xl z-30"
                >
                  <button
                    onClick={handleRegenerate}
                    disabled={isRegenerating}
                    className="w-full px-4 py-2.5 text-left text-sm text-starlight/80
                             hover:bg-white/10 transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    {isRegenerating ? "Regenerating..." : "Regenerate images"}
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Regeneration status */}
      {regenStatus && (
        <div className="text-center pb-2">
          <span className="text-[11px] text-purple-300/80 animate-pulse">{regenStatus}</span>
        </div>
      )}

      {/* Transcript toggle */}
      {transcript && (
        <div className="text-center py-2">
          <button
            onClick={() => setShowTranscript(!showTranscript)}
            className="text-sm text-starlight/60 hover:text-starlight underline cursor-pointer"
          >
            {showTranscript ? "Hide" : "Show"} Transcript
          </button>
        </div>
      )}

      {/* Transcript with illustrations */}
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
    </div>
  );
}
