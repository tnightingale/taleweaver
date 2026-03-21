import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import StoryScreen from "../components/StoryScreen";
import { pollJobStatus, getAudioUrl } from "../api/client";
import type { JobCompleteResponse } from "../types";

export default function StoryRoute() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  
  const [isGenerating, setIsGenerating] = useState(true);
  const [currentStage, setCurrentStage] = useState("writing");
  const [storyTitle, setStoryTitle] = useState("");
  const [storyDuration, setStoryDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState("");
  const [transcript, setTranscript] = useState("");
  const [storyData, setStoryData] = useState<JobCompleteResponse | undefined>(undefined);
  const [error, setError] = useState("");
  const pollingRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  const startPolling = useCallback((id: string) => {
    setIsGenerating(true);
    setCurrentStage("writing");

    pollingRef.current = setInterval(async () => {
      try {
        const status = await pollJobStatus(id);
        if (status.status === "complete" && "title" in status) {
          clearInterval(pollingRef.current);
          const url = getAudioUrl(id);
          setStoryTitle(status.title);
          setStoryDuration(status.duration_seconds);
          setAudioUrl(url);
          setTranscript(status.transcript);
          setStoryData(status);
          setIsGenerating(false);
        } else if (status.status === "failed") {
          clearInterval(pollingRef.current);
          const errorMsg = "error" in status ? status.error : "Story generation failed";
          setError(errorMsg || "Story generation failed");
          setIsGenerating(false);
        } else {
          const stage = "current_stage" in status ? status.current_stage : "writing";
          setCurrentStage(stage || "writing");
        }
      } catch (err) {
        clearInterval(pollingRef.current);
        setError(err instanceof Error ? err.message : "Failed to check story status");
        setIsGenerating(false);
      }
    }, 2000);
  }, []);

  useEffect(() => {
    if (!jobId) {
      navigate("/");
      return;
    }

    // Check if story already completed (from session)
    const saved = sessionStorage.getItem(`taleweaver_story_${jobId}`);
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
      sessionStorage.setItem(`taleweaver_story_${jobId}`, JSON.stringify(storyData));
    }
  }, [storyData, jobId]);

  const handleCreateAnother = () => {
    if (jobId) {
      sessionStorage.removeItem(`taleweaver_story_${jobId}`);
    }
    navigate("/craft");
  };

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="glass-card p-8 max-w-md text-center">
          <div className="text-6xl mb-4">😔</div>
          <h2 className="text-2xl font-display text-glow mb-2">Oops!</h2>
          <p className="text-starlight/60 mb-6">{error}</p>
          <button onClick={() => navigate("/craft")} className="btn-glow">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <StoryScreen
      isGenerating={isGenerating}
      currentStage={currentStage}
      title={storyTitle}
      audioUrl={audioUrl}
      durationSeconds={storyDuration}
      transcript={transcript}
      storyData={storyData}
      onCreateAnother={handleCreateAnother}
    />
  );
}
