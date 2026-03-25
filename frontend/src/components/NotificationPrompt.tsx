import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { usePushNotifications } from "../hooks/usePushNotifications";

const SESSION_KEY = "taleweaver_notif_prompt_dismissed";

export default function NotificationPrompt() {
  const { isSupported, permission, isSubscribed, loading, subscribe } = usePushNotifications();
  const [dismissed, setDismissed] = useState(false);
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (loading) return;

    // Auto-subscribe if permission already granted but not subscribed
    if (permission === "granted" && !isSubscribed) {
      subscribe();
      return;
    }

    // Show prompt if supported, not yet asked, and not dismissed this session
    if (
      isSupported &&
      permission === "default" &&
      !isSubscribed &&
      !sessionStorage.getItem(SESSION_KEY)
    ) {
      setShow(true);
    }
  }, [loading, isSupported, permission, isSubscribed, subscribe]);

  const handleEnable = async () => {
    sessionStorage.setItem(SESSION_KEY, "1");
    await subscribe();
    setShow(false);
  };

  const handleDismiss = () => {
    sessionStorage.setItem(SESSION_KEY, "1");
    setDismissed(true);
    setShow(false);
  };

  if (!show || dismissed) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 10 }}
        className="glass-card p-4 w-full max-w-md mx-auto text-center space-y-3"
      >
        <p className="text-sm text-starlight/80">
          Get notified when your story is ready?
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={handleEnable}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded text-white text-sm font-medium transition-all"
          >
            Enable
          </button>
          <button
            onClick={handleDismiss}
            className="px-4 py-2 text-starlight/50 hover:text-starlight/80 text-sm transition-colors"
          >
            Not now
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
