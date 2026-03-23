import { Routes, Route, useLocation } from "react-router-dom";
import ParticleBackground from "./components/ParticleBackground";
import HeroRoute from "./routes/HeroRoute";
import CraftRoute from "./routes/CraftRoute";
import StoryRoute from "./routes/StoryRoute";
import LibraryRoute from "./routes/LibraryRoute";
import StandalonePlayer from "./components/StandalonePlayer";

export default function App() {
  const location = useLocation();
  const isStoryPermalink = location.pathname.startsWith("/s/");

  return (
    <div className="min-h-screen">
      <ParticleBackground />

      <div className="content-layer min-h-screen flex flex-col">
        {!isStoryPermalink && (
          <header className="py-8 text-center">
            <h1
              className="text-4xl md:text-5xl font-bold tracking-wide text-ethereal"
              style={{
                fontFamily: "var(--font-display)",
                textShadow: "0 0 20px rgba(167, 139, 250, 0.5), 0 0 40px rgba(167, 139, 250, 0.2)",
              }}
            >
              Taleweaver
            </h1>
            <p className="text-starlight/40 mt-2 text-sm tracking-widest uppercase">
              Where stories come alive
            </p>
          </header>
        )}

        <main className={`flex-1 px-4 ${isStoryPermalink ? "pb-4 pt-2" : "pb-16"}`}>
          <Routes>
            <Route path="/" element={<HeroRoute />} />
            <Route path="/craft" element={<CraftRoute />} />
            <Route path="/story/:jobId" element={<StoryRoute />} />
            <Route path="/library" element={<LibraryRoute />} />
            <Route path="/s/:shortId" element={<StandalonePlayer />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
