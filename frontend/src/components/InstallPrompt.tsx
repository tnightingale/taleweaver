import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * Shows a subtle "Add to Home Screen" banner when:
 * - Running in a browser (not standalone PWA)
 * - On a mobile device (iOS or Android)
 * - User hasn't dismissed it before
 */
export default function InstallPrompt() {
  const [show, setShow] = useState(false);
  const [isIOS, setIsIOS] = useState(false);

  useEffect(() => {
    // Don't show if already in standalone mode
    const isStandalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      ("standalone" in navigator && (navigator as unknown as { standalone: boolean }).standalone);
    if (isStandalone) return;

    // Only show on mobile
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    if (!isMobile) return;

    // Don't show if dismissed recently (7 days)
    const dismissed = localStorage.getItem("tw-install-dismissed");
    if (dismissed && Date.now() - Number(dismissed) < 7 * 24 * 60 * 60 * 1000) return;

    setIsIOS(/iPhone|iPad|iPod/.test(navigator.userAgent));
    // Small delay so it doesn't flash on initial load
    const timer = setTimeout(() => setShow(true), 3000);
    return () => clearTimeout(timer);
  }, []);

  const dismiss = () => {
    setShow(false);
    localStorage.setItem("tw-install-dismissed", String(Date.now()));
  };

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 50 }}
          transition={{ type: "spring", damping: 25 }}
          className="fixed bottom-20 sm:bottom-6 left-4 right-4 z-40 max-w-sm mx-auto"
        >
          <div className="glass-card p-4 shadow-xl border border-mystic/20">
            <div className="flex items-start gap-3">
              <div className="text-2xl shrink-0">📖</div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-starlight">
                  Add to Home Screen
                </p>
                <p className="text-xs text-starlight/60 mt-1">
                  {isIOS
                    ? "Tap the share button, then \"Add to Home Screen\" for fullscreen stories."
                    : "Install Story Spring for fullscreen stories and offline playback."}
                </p>
              </div>
              <button
                onClick={dismiss}
                className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center
                         text-starlight/40 hover:text-starlight hover:bg-white/10
                         transition-all cursor-pointer text-xs"
              >
                ✕
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
