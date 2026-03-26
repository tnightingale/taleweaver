import { useRef, useState, useEffect, type ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { JobCompleteResponse } from "../types";
import IllustratedStoryPlayer from "./IllustratedStoryPlayer";
import ProgressRing from "./ProgressRing";
import { useFullscreen } from "../hooks/useFullscreen";
import { useMediaSession } from "../hooks/useMediaSession";
import { useAirPlay } from "../hooks/useAirPlay";
import { useChromecast } from "../hooks/useChromecast";
import { useWakeLock } from "../hooks/useWakeLock";
import CastButton from "./CastButton";
import { STAGE_LABELS } from "../constants/stages";
import NotificationPrompt from "./NotificationPrompt";
import type { ProgressData } from "../types";

interface Props {
  isGenerating: boolean;
  currentStage?: string;
  progress?: number;
  progressDetail?: string;
  title: string;
  audioUrl: string;
  durationSeconds: number;
  transcript?: string;
  storyData?: JobCompleteResponse;
  onCreateAnother: () => void;
  onBackToLibrary?: () => void;
  offlineStatus?: ReactNode;
  readOnly?: boolean;
  partialTitle?: string | null;
  partialTranscript?: string | null;
  completedIllustrations?: string[];
  progressData?: ProgressData | null;
  coverImageUrl?: string | null;
  initialLoading?: boolean;
}

const formatTime = (seconds: number) => {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
};

export default function StoryScreen({
  isGenerating,
  currentStage,
  progress = 0,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  progressDetail: _progressDetail = "",
  title,
  audioUrl,
  durationSeconds,
  transcript,
  storyData,
  onCreateAnother,
  onBackToLibrary,
  offlineStatus,
  readOnly = false,
  partialTitle,
  partialTranscript,
  completedIllustrations = [],
  progressData,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  coverImageUrl: _coverImageUrl,
  initialLoading = false,
}: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const playerRef = useRef<HTMLDivElement>(null);
  const { isFullscreen, toggleFullscreen, isSupported: fullscreenSupported } = useFullscreen(playerRef);
  const [isPlaying, setIsPlaying] = useState(false);
  useWakeLock(isPlaying);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(durationSeconds);
  const [isSeeking, setIsSeeking] = useState(false);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [showTranscript, setShowTranscript] = useState(false);
  const [copied, setCopied] = useState(false);

  const { isAvailable: airPlayAvailable, isActive: airPlayActive, showPicker: showAirPlayPicker } = useAirPlay(audioRef);
  const chromecast = useChromecast();

  const isCasting = chromecast.isConnected;

  const handleMediaSeekTo = (time: number) => {
    if (isCasting) {
      chromecast.seek(time);
    } else if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
    setCurrentTime(time);
  };

  useMediaSession({
    title,
    artwork: undefined,
    isPlaying,
    duration: isCasting ? chromecast.duration : duration,
    currentTime: isCasting ? chromecast.currentTime : currentTime,
    onPlay: () => {
      if (isCasting) chromecast.playOrPause();
      else audioRef.current?.play().catch(() => {});
    },
    onPause: () => {
      if (isCasting) chromecast.playOrPause();
      else audioRef.current?.pause();
    },
    onSeekTo: handleMediaSeekTo,
  });

  // Sync Chromecast state to local state when casting
  useEffect(() => {
    if (!isCasting) return;
    setCurrentTime(chromecast.currentTime);
    setIsPlaying(!chromecast.isPaused);
    if (chromecast.duration > 0) setDuration(chromecast.duration);
  }, [isCasting, chromecast.currentTime, chromecast.isPaused, chromecast.duration]);

  // Sync duration from props when they change
  useEffect(() => {
    if (!isCasting) setDuration(durationSeconds);
  }, [durationSeconds, isCasting]);

  const handleLoadedMetadata = () => {
    if (audioRef.current && audioRef.current.duration && isFinite(audioRef.current.duration)) {
      setDuration(audioRef.current.duration);
    }
  };

  const togglePlay = () => {
    if (isCasting) {
      chromecast.playOrPause();
      return;
    }
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
    if (isCasting) {
      chromecast.seek(t);
    } else if (audioRef.current) {
      audioRef.current.currentTime = t;
    }
    setCurrentTime(t);
  };

  const handleCastClick = () => {
    if (isCasting) {
      chromecast.disconnect();
    } else {
      // Build absolute audio URL for Chromecast to fetch directly
      const absoluteAudioUrl = audioUrl.startsWith("http")
        ? audioUrl
        : `${window.location.origin}${audioUrl}`;
      chromecast.cast({ audioUrl: absoluteAudioUrl, title });
      // Pause local audio when starting cast
      audioRef.current?.pause();
    }
  };

  const handleSeekStart = () => setIsSeeking(true);
  const handleSeekEnd = () => setIsSeeking(false);

  const handleTimeUpdate = () => {
    if (!isSeeking && audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleAudioError = () => {
    setAudioError("Failed to load audio. Please try again.");
    setIsPlaying(false);
  };

  // Build download URL with ?download=true
  const downloadUrl = audioUrl ? `${audioUrl}?download=true` : "";

  return (
    <div ref={playerRef} className={`flex flex-col items-center justify-center min-h-[60vh] ${isFullscreen ? "bg-void h-screen" : ""} ${storyData?.has_illustrations && storyData?.scenes ? "sm:px-4" : "px-4"}`}>
      <AnimatePresence mode="wait">
        {isGenerating && initialLoading ? (
          /* ─── Loading spinner while fetching current state ─── */
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center space-y-4"
          >
            <div className="w-12 h-12 rounded-full border-2 border-mystic/30 border-t-mystic animate-spin" />
            <p className="text-sm text-starlight/40">Loading story...</p>
          </motion.div>
        ) : isGenerating ? (
          /* ─── Progressive Generation View ─── */
          <motion.div
            key="generating"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.5 }}
            className="flex flex-col items-center space-y-6 w-full max-w-2xl px-4"
          >
            {/* Title — real when available, placeholder before */}
            <AnimatePresence mode="wait">
              <motion.h2
                key={partialTitle || "placeholder"}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="text-2xl md:text-3xl font-display text-glow text-center leading-snug"
              >
                {partialTitle || "Creating your story..."}
              </motion.h2>
            </AnimatePresence>

            {/* Progress ring (smaller) + percentage + stage */}
            <div className="flex flex-col items-center space-y-3">
              <ProgressRing progress={progress}>
                <motion.div
                  className="w-20 h-20 rounded-full orb-color-cycle"
                  animate={{ scale: [1, 1.1, 1], opacity: [0.8, 1, 0.8] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                />
              </ProgressRing>

              <div className="text-center space-y-1">
                <motion.p
                  className="text-xl font-mono text-glow"
                  key={Math.round(progress)}
                  initial={{ scale: 1.1, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  {Math.round(progress)}%
                </motion.p>
                <p className="text-sm text-ethereal">
                  {currentStage ? (STAGE_LABELS[currentStage] ?? "Creating your story...") : "Creating your story..."}
                </p>
              </div>

              {/* Structured progress detail */}
              {progressData && (
                <div className="flex gap-4 text-xs text-starlight/50">
                  {progressData.voice && (
                    <span>Voices: {progressData.voice.completed}/{progressData.voice.total}</span>
                  )}
                  {progressData.illustrations && (
                    <span>Illustrations: {progressData.illustrations.completed}/{progressData.illustrations.total}</span>
                  )}
                </div>
              )}
            </div>

            <style>{`
              @keyframes orbColorCycle {
                0%   { background: radial-gradient(circle, #4ade80 0%, #16a34a 50%, #14532d 100%);
                       box-shadow: 0 0 40px rgba(22,163,74,0.6), 0 0 80px rgba(22,163,74,0.3); }
                25%  { background: radial-gradient(circle, #93c5fd 0%, #3b82f6 50%, #1e3a8a 100%);
                       box-shadow: 0 0 40px rgba(59,130,246,0.6), 0 0 80px rgba(59,130,246,0.3); }
                50%  { background: radial-gradient(circle, #fb923c 0%, #f97316 50%, #7c2d12 100%);
                       box-shadow: 0 0 40px rgba(249,115,22,0.6), 0 0 80px rgba(249,115,22,0.3); }
                75%  { background: radial-gradient(circle, #6ee7b7 0%, #10b981 50%, #064e3b 100%);
                       box-shadow: 0 0 40px rgba(16,185,129,0.6), 0 0 80px rgba(16,185,129,0.3); }
                100% { background: radial-gradient(circle, #4ade80 0%, #16a34a 50%, #14532d 100%);
                       box-shadow: 0 0 40px rgba(22,163,74,0.6), 0 0 80px rgba(22,163,74,0.3); }
              }
              .orb-color-cycle {
                animation: orbColorCycle 8s ease-in-out infinite;
              }
            `}</style>

            {/* Illustration gallery — images fade in as they arrive */}
            {completedIllustrations.length > 0 && (
              <div className="w-full">
                <p className="text-xs text-starlight/40 mb-2">Illustrations</p>
                <div className="grid grid-cols-3 gap-2">
                  {completedIllustrations.map((url, i) => (
                    <motion.img
                      key={url}
                      src={url}
                      alt={`Scene ${i + 1}`}
                      className="w-full aspect-[3/2] object-cover rounded-lg"
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.5, delay: i * 0.1 }}
                    />
                  ))}
                  {progressData?.illustrations && Array.from(
                    { length: Math.max(0, progressData.illustrations.total - completedIllustrations.length) },
                    (_, i) => (
                      <div
                        key={`placeholder-${i}`}
                        className="w-full aspect-[3/2] rounded-lg bg-gradient-to-br from-deep/30 to-abyss/40 animate-pulse"
                      />
                    )
                  )}
                </div>
              </div>
            )}

            {/* Transcript preview */}
            {partialTranscript && (
              <details className="w-full glass-card">
                <summary className="px-4 py-3 cursor-pointer text-sm text-starlight/60 hover:text-starlight/80 transition-colors">
                  Read the story (preview)
                </summary>
                <div className="px-4 pb-4 max-h-48 overflow-y-auto">
                  <p className="text-sm text-starlight/70 leading-relaxed whitespace-pre-line">
                    {partialTranscript}
                  </p>
                </div>
              </details>
            )}

            {/* Push notification prompt */}
            <NotificationPrompt />

            {/* Back to Library */}
            {onBackToLibrary && (
              <button
                onClick={onBackToLibrary}
                className="text-sm text-starlight/40 hover:text-starlight/70 transition-colors"
              >
                ← Back to Library
              </button>
            )}
          </motion.div>
        ) : (
          audioUrl && (
            /* ─── Phase 2: Audio Player (Illustrated or Standard) ─── */
            storyData?.has_illustrations && storyData?.scenes ? (
              /* Illustrated Player with Page Turn Animation */
              <IllustratedStoryPlayer
                key="illustrated-player"
                audioUrl={audioUrl}
                scenes={storyData.scenes}
                title={title}
                shortId={storyData.short_id}
                storyId={storyData.job_id}
                artStyle={storyData.art_style}
                durationSeconds={durationSeconds}
                transcript={transcript}
                onCreateAnother={onCreateAnother}
                onBackToLibrary={onBackToLibrary}
                offlineStatus={offlineStatus}
                readOnly={readOnly}
                videoUrl={storyData.video_url}
              />
            ) : (
              /* Standard Audio Player */
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
                {audioError ? (
                  <p className="text-red-400 text-center text-sm">{audioError}</p>
                ) : (
                  <>
                    {/* Seek Bar */}
                    <input
                      type="range"
                      min={0}
                      max={duration || 1}
                      step={0.1}
                      value={currentTime}
                      onChange={handleSeek}
                      onMouseDown={handleSeekStart}
                      onMouseUp={handleSeekEnd}
                      onTouchStart={handleSeekStart}
                      onTouchEnd={handleSeekEnd}
                      className="w-full h-2 rounded-full appearance-none cursor-pointer
                        bg-white/10
                        [&::-webkit-slider-thumb]:appearance-none
                        [&::-webkit-slider-thumb]:w-4
                        [&::-webkit-slider-thumb]:h-4
                        [&::-webkit-slider-thumb]:rounded-full
                        [&::-webkit-slider-thumb]:bg-mystic
                        [&::-webkit-slider-thumb]:shadow-[0_0_10px_rgba(22,163,74,0.6)]
                        [&::-webkit-slider-runnable-track]:rounded-full
                        [&::-moz-range-thumb]:w-4
                        [&::-moz-range-thumb]:h-4
                        [&::-moz-range-thumb]:rounded-full
                        [&::-moz-range-thumb]:bg-mystic
                        [&::-moz-range-thumb]:border-none
                        [&::-moz-range-thumb]:shadow-[0_0_10px_rgba(22,163,74,0.6)]
                        accent-mystic"
                    />

                    {/* Time Display */}
                    <div className="flex justify-between text-sm text-starlight/40">
                      <span>{formatTime(currentTime)}</span>
                      <span>{formatTime(duration)}</span>
                    </div>

                    {/* Play/Pause Button + Fullscreen */}
                    <div className="flex items-center justify-center gap-4">
                      <motion.button
                        onClick={togglePlay}
                        whileTap={{ scale: 0.9 }}
                        whileHover={{
                          boxShadow:
                            "0 0 30px rgba(22, 163, 74, 0.6), 0 0 60px rgba(22, 163, 74, 0.3)",
                        }}
                        className="w-20 h-20 sm:w-20 sm:h-20 rounded-full flex items-center justify-center text-3xl text-white cursor-pointer"
                        style={{
                          background:
                            "linear-gradient(135deg, #16a34a, #15803d)",
                          boxShadow:
                            "0 0 20px rgba(22, 163, 74, 0.4), 0 0 40px rgba(22, 163, 74, 0.15)",
                        }}
                      >
                        {isPlaying ? "⏸" : "▶"}
                      </motion.button>
                      {airPlayAvailable && (
                        <button
                          onClick={showAirPlayPicker}
                          className={`w-10 h-10 rounded-full flex items-center justify-center
                                   transition-all cursor-pointer
                                   ${airPlayActive
                                     ? "text-mystic bg-mystic/20"
                                     : "text-starlight/60 hover:text-starlight hover:bg-white/10"
                                   }`}
                          title={airPlayActive ? "AirPlay active" : "AirPlay"}
                        >
                          <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                            <path d="M6 22h12l-6-6-6 6zM21 3H3c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h4v-2H3V5h18v12h-4v2h4c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z" />
                          </svg>
                        </button>
                      )}
                      <CastButton
                        isAvailable={chromecast.isAvailable}
                        isConnected={chromecast.isConnected}
                        deviceName={chromecast.deviceName}
                        onClick={handleCastClick}
                      />
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
                  </>
                )}

                {/* Casting Indicator */}
                {(airPlayActive || isCasting) && (
                  <p className="text-center text-sm text-mystic/80 animate-pulse">
                    {airPlayActive
                      ? "Playing on AirPlay"
                      : `Casting to ${chromecast.deviceName ?? "device"}`}
                  </p>
                )}

                {/* Hidden Audio Element */}
                <audio
                  ref={audioRef}
                  src={audioUrl}
                  preload="auto"
                  x-webkit-airplay="allow"
                  onLoadedMetadata={handleLoadedMetadata}
                  onTimeUpdate={handleTimeUpdate}
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  onEnded={() => setIsPlaying(false)}
                  onError={handleAudioError}
                />
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-4 w-full">
                <a
                  href={downloadUrl}
                  download={`${title}.mp3`}
                  className="glass-card px-6 py-3 text-center font-semibold text-starlight transition-all hover:text-glow"
                >
                  Download MP3
                </a>
                {onBackToLibrary ? (
                  <>
                    <button
                      onClick={onBackToLibrary}
                      className="glass-card px-6 py-3 text-center font-semibold text-starlight transition-all hover:text-glow"
                    >
                      ← Back to Library
                    </button>
                    <button
                      onClick={onCreateAnother}
                      className="btn-glow flex-1 text-center"
                    >
                      Create Another
                    </button>
                  </>
                ) : (
                  <button
                    onClick={onCreateAnother}
                    className="btn-glow flex-1 text-center"
                  >
                    Create Another Story
                  </button>
                )}
              </div>

              {/* Permalink Share Section */}
              {storyData?.short_id && (
                <div className="w-full glass-card p-4">
                  <p className="text-ethereal text-sm mb-3 font-medium">
                    Share this story:
                  </p>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={`${window.location.origin}/s/${storyData.short_id}`}
                      className="flex-1 px-3 py-2 bg-black/50 border border-mystic/50
                                 rounded text-starlight text-sm font-mono"
                      onClick={(e) => e.currentTarget.select()}
                    />
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(
                          `${window.location.origin}/s/${storyData.short_id}`
                        );
                        setCopied(true);
                        setTimeout(() => setCopied(false), 2000);
                      }}
                      className="px-4 py-2 bg-accent hover:bg-mystic rounded
                                 text-white text-sm font-semibold transition-all
                                 hover:shadow-lg hover:shadow-mystic/50"
                    >
                      {copied ? "Copied!" : "Copy Link"}
                    </button>
                  </div>
                </div>
              )}

              {/* Transcript Toggle */}
              {transcript && (
                <div className="w-full">
                  <button
                    onClick={() => setShowTranscript(!showTranscript)}
                    className="w-full text-center text-sm text-starlight/50 hover:text-starlight/80 transition-colors py-2 cursor-pointer"
                  >
                    {showTranscript ? "Hide Story Text" : "Read the Story"}{" "}
                    <span className="inline-block transition-transform" style={{ transform: showTranscript ? "rotate(180deg)" : "rotate(0deg)" }}>
                      ▾
                    </span>
                  </button>
                  <AnimatePresence>
                    {showTranscript && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3, ease: "easeInOut" }}
                        className="overflow-hidden"
                      >
                        <div className="glass-card p-6 mt-2 max-h-96 overflow-y-auto">
                          <div className="text-starlight/80 text-sm leading-relaxed whitespace-pre-line">
                            {transcript}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )}
            </motion.div>
            )
          )
        )}
      </AnimatePresence>
    </div>
  );
}
