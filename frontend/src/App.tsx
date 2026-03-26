import { Routes, Route, useLocation, Link } from "react-router-dom";
import ParticleBackground from "./components/ParticleBackground";
import ProtectedRoute from "./components/ProtectedRoute";
import HeroRoute from "./routes/HeroRoute";
import CraftRoute from "./routes/CraftRoute";
import StoryRoute from "./routes/StoryRoute";
import LibraryRoute from "./routes/LibraryRoute";
import LoginRoute from "./routes/LoginRoute";
import SignupRoute from "./routes/SignupRoute";
import AccountRoute from "./routes/AccountRoute";
import StandalonePlayer from "./components/StandalonePlayer";
import InstallPrompt from "./components/InstallPrompt";
import { useAuth } from "./contexts/AuthContext";

export default function App() {
  const location = useLocation();
  const isStoryPermalink = location.pathname.startsWith("/s/");
  const isAuthPage = location.pathname === "/login" || location.pathname === "/signup";
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen">
      <ParticleBackground />

      <div className="content-layer min-h-screen flex flex-col">
        {!isStoryPermalink && (
          <header className="py-8 text-center relative">
            {user && !isAuthPage && (
              <div className="absolute right-4 top-4 flex items-center gap-3">
                <Link
                  to="/account"
                  className="text-starlight/40 hover:text-starlight/60 text-sm transition-colors"
                  title="Account settings"
                >
                  <span className="hidden sm:inline">{user.display_name}</span>
                  <svg className="w-4 h-4 sm:hidden" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </Link>
                <button
                  onClick={logout}
                  className="text-starlight/30 hover:text-starlight/60 text-sm transition-colors"
                >
                  Sign out
                </button>
              </div>
            )}
            <Link to="/">
              <h1
                className="text-4xl md:text-5xl font-bold tracking-wide text-ethereal"
                style={{
                  fontFamily: "var(--font-display)",
                  textShadow: "0 0 20px rgba(167, 139, 250, 0.5), 0 0 40px rgba(167, 139, 250, 0.2)",
                }}
              >
                Taleweaver
              </h1>
            </Link>
            <p className="text-starlight/40 mt-2 text-sm tracking-widest uppercase">
              Where stories come alive
            </p>
          </header>
        )}

        <main className={`flex-1 ${isStoryPermalink ? "px-0 sm:px-4 pb-4 pt-0 sm:pt-2" : "px-4 pb-16"}`}>
          <Routes>
            <Route path="/login" element={<LoginRoute />} />
            <Route path="/signup" element={<SignupRoute />} />
            <Route path="/" element={<ProtectedRoute><HeroRoute /></ProtectedRoute>} />
            <Route path="/craft" element={<ProtectedRoute><CraftRoute /></ProtectedRoute>} />
            <Route path="/story/:jobId" element={<ProtectedRoute><StoryRoute /></ProtectedRoute>} />
            <Route path="/library" element={<ProtectedRoute><LibraryRoute /></ProtectedRoute>} />
            <Route path="/account" element={<ProtectedRoute><AccountRoute /></ProtectedRoute>} />
            <Route path="/s/:shortId" element={<StandalonePlayer />} />
          </Routes>
        </main>
      </div>
      <InstallPrompt />
    </div>
  );
}
