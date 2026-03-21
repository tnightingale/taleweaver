import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import CraftScreen from "../components/CraftScreen";
import { createCustomStory, createHistoricalStory } from "../api/client";
import type { KidProfile, StoryType, StoryMood, StoryLength } from "../types";

export default function CraftRoute() {
  const navigate = useNavigate();
  
  // Load craft data from session storage
  const [craftData, setCraftData] = useState<{profile: KidProfile; type: StoryType} | null>(null);
  const [mood, setMood] = useState<StoryMood | undefined>(undefined);
  const [length, setLength] = useState<StoryLength | undefined>(undefined);

  useEffect(() => {
    const saved = sessionStorage.getItem("taleweaver_craft_data");
    if (saved) {
      setCraftData(JSON.parse(saved));
    } else {
      // No profile data, go back to hero
      navigate("/");
    }
  }, [navigate]);

  if (!craftData) {
    return null; // Redirecting...
  }

  const handleCustomStory = async (genre: string, description: string) => {
    try {
      const response = await createCustomStory(
        craftData.profile,
        genre,
        description,
        mood,
        length
      );
      // Navigate to story generation page
      navigate(`/story/${response.job_id}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create story");
    }
  };

  const handleHistoricalStory = async (eventId: string) => {
    try {
      const response = await createHistoricalStory(
        craftData.profile,
        eventId,
        mood,
        length
      );
      navigate(`/story/${response.job_id}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create story");
    }
  };

  const handleBack = () => {
    sessionStorage.removeItem("taleweaver_craft_data");
    navigate("/");
  };

  const handleViewLibrary = () => {
    navigate("/library");
  };

  return (
    <CraftScreen
      storyType={craftData.type}
      mood={mood}
      length={length}
      onMoodChange={setMood}
      onLengthChange={setLength}
      onSubmitCustom={handleCustomStory}
      onSubmitHistorical={handleHistoricalStory}
      onBack={handleBack}
      onTypeChange={(type) => {
        setCraftData({ ...craftData, type });
        sessionStorage.setItem(
          "taleweaver_craft_data",
          JSON.stringify({ ...craftData, type })
        );
      }}
      onViewLibrary={handleViewLibrary}
    />
  );
}
