import { useNavigate } from "react-router-dom";
import HeroScreen from "../components/HeroScreen";
import type { KidProfile, StoryType } from "../types";

export default function HeroRoute() {
  const navigate = useNavigate();

  const handleSubmit = (profile: KidProfile, type: StoryType) => {
    // Save profile and type to session storage for use in craft
    sessionStorage.setItem(
      "taleweaver_craft_data",
      JSON.stringify({ profile, type })
    );
    navigate("/craft");
  };

  const handleViewLibrary = () => {
    navigate("/library");
  };

  return <HeroScreen onSubmit={handleSubmit} onViewLibrary={handleViewLibrary} />;
}
