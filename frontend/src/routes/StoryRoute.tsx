import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import StoryScreen from "../components/StoryScreen";
import { pollJobStatus, retryJob } from "../api/client";
import type { JobCompleteResponse, ProgressData } from "../types";

export default function StoryRoute() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  
  const [isGenerating, setIsGenerating] = useState(true);
  const [currentStage, setCurrentStage] = useState("writing");
  const [progress, setProgress] = useState(0);
  const [progressDetail, setProgressDetail] = useState("");
  const [storyTitle, setStoryTitle] = useState("");
  const [storyDuration, setStoryDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState("");
  const [transcript, setTranscript] = useState("");
  const [storyData, setStoryData] = useState<JobCompleteResponse | undefined>(undefined);
  const [error, setError] = useState("");
  const [partialTitle, setPartialTitle] = useState<string | null>(null);
  const [partialTranscript, setPartialTranscript] = useState<string | null>(null);
  const [completedIllustrations, setCompletedIllustrations] = useState<string[]>([]);
  const [progressData, setProgressData] = useState<ProgressData | null>(null);
  const [coverImageUrl, setCoverImageUrl] = useState<string | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const pollingRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const progressHighWater = useRef(0);

  const handleStatusUpdate = useCallback((status: import("../types").JobStatusResponse | import("../types").JobCompleteResponse) => {
    if (status.status === "complete" && "audio_url" in status) {
      clearInterval(pollingRef.current);
      const complete = status as import("../types").JobCompleteResponse;
      setStoryTitle(complete.title);
      setStoryDuration(complete.duration_seconds);
      setAudioUrl(complete.audio_url);
      setTranscript(complete.transcript);
      setStoryData(complete);
      setIsGenerating(false);
    } else if (status.status === "failed") {
      clearInterval(pollingRef.current);
      const errorMsg = "error" in status ? status.error : "Story generation failed";
      setError(errorMsg || "Story generation failed");
      setIsGenerating(false);
    } else {
      const stage = "current_stage" in status ? status.current_stage : "writing";
      setCurrentStage(stage || "writing");
      const newProgress = status.progress || 0;
      if (newProgress >= progressHighWater.current) {
        progressHighWater.current = newProgress;
        setProgress(newProgress);
      }
      setProgressDetail(status.progress_detail || "");

      if ("title" in status && status.title) setPartialTitle(status.title);
      if ("transcript" in status && status.transcript) setPartialTranscript(status.transcript);
      if ("completed_illustrations" in status && status.completed_illustrations) setCompletedIllustrations(status.completed_illustrations);
      if ("progress_data" in status && status.progress_data) setProgressData(status.progress_data);
      if ("cover_image_url" in status && status.cover_image_url) setCoverImageUrl(status.cover_image_url);
    }
  }, []);

  const startPolling = useCallback((id: string) => {
    setIsGenerating(true);
    setCurrentStage("writing");
    progressHighWater.current = 0;

    // Immediate first poll to avoid showing stale 0% state
    pollJobStatus(id)
      .then(status => handleStatusUpdate(status))
      .catch(err => {
        setError(err instanceof Error ? err.message : "Failed to check story status");
        setIsGenerating(false);
      })
      .finally(() => setInitialLoading(false));

    pollingRef.current = setInterval(async () => {
      try {
        const status = await pollJobStatus(id);
        handleStatusUpdate(status);
      } catch (err) {
        clearInterval(pollingRef.current);
        setError(err instanceof Error ? err.message : "Failed to check story status");
        setIsGenerating(false);
      }
    }, 2000);
  }, [handleStatusUpdate]);

  useEffect(() => {
    if (!jobId) {
      navigate("/");
      return;
    }

    // Check if story already completed (from session)
    const saved = sessionStorage.getItem(`storyspring_story_${jobId}`);
    if (saved) {
      const data = JSON.parse(saved);
      if (data.status === "complete") {
        setStoryTitle(data.title);
        setStoryDuration(data.duration_seconds);
        setAudioUrl(data.audio_url);
        setTranscript(data.transcript);
        setStoryData(data);
        setIsGenerating(false);
        return;
      }
    }

    // Start polling for generation
    startPolling(jobId);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [jobId, navigate, startPolling]);

  // Save completed story to session for refresh persistence
  useEffect(() => {
    if (storyData && jobId) {
      sessionStorage.setItem(`storyspring_story_${jobId}`, JSON.stringify(storyData));
    }
  }, [storyData, jobId]);

  const handleCreateAnother = () => {
    if (jobId) {
      sessionStorage.removeItem(`storyspring_story_${jobId}`);
    }
    navigate("/craft");
  };

  const handleBackToLibrary = () => {
    navigate("/library");
  };

  const handleRetry = async () => {
    if (!jobId) return;
    
    try {
      setError("");
      setIsGenerating(true);
      await retryJob(jobId);
      // Resume polling
      startPolling(jobId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to retry. Please try again.");
      setIsGenerating(false);
    }
  };

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="glass-card p-8 max-w-md text-center space-y-4">
          <div className="text-6xl">😔</div>
          <h2 className="text-2xl font-display text-glow">Generation Failed</h2>
          <p className="text-starlight/60">{error}</p>
          
          {/* Show partial progress if available */}
          {storyData?.partial_progress && (
            <div className="glass-card p-4 space-y-2 text-left bg-starlight/5">
              <p className="text-sm font-semibold text-starlight/80">Progress before failure:</p>
              <ul className="text-sm text-starlight/60 space-y-1">
                {storyData.partial_progress.segments_completed && (
                  <li>
                    ✅ Voice: {storyData.partial_progress.segments_completed} of{" "}
                    {storyData.partial_progress.segments_total} segments
                  </li>
                )}
                {storyData.partial_progress.illustrations_completed && (
                  <li>
                    ✅ Images: {storyData.partial_progress.illustrations_completed} of{" "}
                    {storyData.partial_progress.illustrations_total} illustrations
                  </li>
                )}
              </ul>
            </div>
          )}
          
          <div className="flex gap-3 justify-center">
            {/* Retry button if resumable */}
            {storyData?.resumable && (
              <button onClick={handleRetry} className="btn-glow text-sm cursor-pointer">
                🔄 Try Again
                {(storyData.retry_count || 0) > 0 && ` (${storyData.retry_count}/3)`}
              </button>
            )}
            
            {/* Start over button */}
            <button 
              onClick={() => navigate("/craft")} 
              className="px-6 py-3 rounded-xl glass-card text-ethereal hover:text-white text-sm transition-all cursor-pointer"
            >
              ✨ Start Over
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <StoryScreen
      isGenerating={isGenerating}
      currentStage={currentStage}
      progress={progress}
      progressDetail={progressDetail}
      title={storyTitle}
      audioUrl={audioUrl}
      durationSeconds={storyDuration}
      transcript={transcript}
      storyData={storyData}
      onCreateAnother={handleCreateAnother}
      onBackToLibrary={handleBackToLibrary}
      partialTitle={partialTitle}
      partialTranscript={partialTranscript}
      completedIllustrations={completedIllustrations}
      progressData={progressData}
      coverImageUrl={coverImageUrl}
      initialLoading={initialLoading}
    />
  );
}
