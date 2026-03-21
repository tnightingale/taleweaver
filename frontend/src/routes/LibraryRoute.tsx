import { useNavigate } from "react-router-dom";
import LibraryScreen from "../components/LibraryScreen";
import type { StoryMetadata } from "../types";

export default function LibraryRoute() {
  const navigate = useNavigate();

  const handleClose = () => {
    navigate("/");
  };

  const handlePlayStory = (story: StoryMetadata) => {
    // Navigate to standalone player for the story
    navigate(`/s/${story.short_id}`);
  };

  return <LibraryScreen onClose={handleClose} onPlayStory={handlePlayStory} />;
}
