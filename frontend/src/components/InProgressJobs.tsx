import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { fetchRecentJobs, type RecentJob } from "../api/client";

const STAGE_LABELS: Record<string, string> = {
  writing: "Writing the story...",
  analyzing_scenes: "Analyzing story structure...",
  splitting: "Preparing character voices...",
  synthesizing: "Generating audio...",
  generating_illustrations: "Creating illustrations...",
  stitching: "Mixing the final track...",
  finalizing: "Adding final touches...",
};

export default function InProgressJobs() {
  const [jobs, setJobs] = useState<RecentJob[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const loadJobs = async () => {
      try {
        const data = await fetchRecentJobs();
        // Filter for in-progress jobs only
        const inProgress = data.jobs.filter(j => j.status === "processing");
        setJobs(inProgress);
      } catch (err) {
        console.error("Failed to load recent jobs:", err);
      } finally {
        setLoading(false);
      }
    };

    loadJobs();

    // Refresh every 5 seconds if there are in-progress jobs
    const interval = setInterval(loadJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return null; // Don't show anything while loading
  }

  if (jobs.length === 0) {
    return null; // Don't show if no in-progress jobs
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-6"
    >
      <div className="glass-card p-6 max-w-2xl mx-auto">
        <h3 className="text-lg font-display text-glow mb-4">
          📖 Story Generating...
        </h3>

        <div className="space-y-3">
          {jobs.map((job) => (
            <motion.button
              key={job.job_id}
              onClick={() => navigate(`/story/${job.job_id}`)}
              className="w-full glass-card p-4 text-left hover:shadow-[0_0_20px_rgba(124,58,237,0.4)] transition-all cursor-pointer"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="font-semibold text-starlight">
                    {job.title || STAGE_LABELS[job.current_stage] || "Generating..."}
                  </p>
                  <p className="text-sm text-starlight/60 mt-1">
                    {Math.round(job.progress)}% complete
                  </p>
                </div>
                <div className="text-2xl ml-4 animate-pulse">⏳</div>
              </div>

              {/* Progress bar */}
              <div className="mt-3 w-full h-1 bg-starlight/10 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-purple-500 to-blue-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${job.progress}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
            </motion.button>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
