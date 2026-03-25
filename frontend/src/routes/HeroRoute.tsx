import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import HeroScreen from "../components/HeroScreen";
import { fetchRecentJobs } from "../api/client";
import type { KidProfile, StoryType } from "../types";

export default function HeroRoute() {
  const navigate = useNavigate();
  const [activeJobCount, setActiveJobCount] = useState(0);

  useEffect(() => {
    fetchRecentJobs()
      .then(data => {
        setActiveJobCount(data.jobs.filter(j => j.status === "processing").length);
      })
      .catch(() => {});
  }, []);

  const handleSubmit = (profile: KidProfile, type: StoryType) => {
    sessionStorage.setItem(
      "taleweaver_craft_data",
      JSON.stringify({ profile, type })
    );
    navigate("/craft");
  };

  const handleViewLibrary = () => {
    navigate("/library");
  };

  return (
    <HeroScreen
      onSubmit={handleSubmit}
      onViewLibrary={handleViewLibrary}
      activeJobCount={activeJobCount}
    />
  );
}
