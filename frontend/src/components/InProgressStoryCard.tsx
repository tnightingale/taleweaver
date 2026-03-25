import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import type { RecentJob } from "../api/client";
import { STAGE_LABELS } from "../constants/stages";

interface Props {
  job: RecentJob;
}

export default function InProgressStoryCard({ job }: Props) {
  const navigate = useNavigate();

  const displayTitle = job.title
    || (job.kid_name && job.genre
      ? `${job.kid_name}'s ${job.genre} story`
      : job.kid_name
        ? `${job.kid_name}'s story`
        : "New story");

  const stageLabel = STAGE_LABELS[job.current_stage] ?? "Creating your story...";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ y: -4 }}
      onClick={() => navigate(`/story/${job.job_id}`)}
      className="glass-card flex flex-col relative cursor-pointer
                 hover:shadow-[0_0_20px_rgba(124,58,237,0.4)] transition-all"
    >
      {/* Cover area */}
      {job.cover_image_url ? (
        <div className="aspect-[3/2] w-full overflow-hidden rounded-t-[1rem]">
          <motion.img
            src={job.cover_image_url}
            alt={displayTitle}
            className="w-full h-full object-cover"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          />
        </div>
      ) : (
        <div className="aspect-[3/2] w-full rounded-t-[1rem] overflow-hidden
                        bg-gradient-to-br from-purple-900/40 to-abyss/60
                        flex items-center justify-center relative">
          <div className="absolute inset-0 shimmer-effect" />
          <div className="text-4xl opacity-30 animate-pulse">
            {job.art_style ? "🎨" : "✨"}
          </div>
        </div>
      )}

      <div className="p-4 flex flex-col gap-2">
        <h3 className="text-base font-display text-glow line-clamp-2 leading-snug">
          {displayTitle}
        </h3>

        <p className="text-xs text-starlight/50">
          {stageLabel} {Math.round(job.progress)}%
        </p>

        <div className="flex items-center gap-1.5 text-xs text-starlight/40">
          {job.kid_name && <span>{job.kid_name}</span>}
          {job.kid_age && (
            <>
              <span>,</span>
              <span>{job.kid_age}</span>
            </>
          )}
          {job.genre && (
            <>
              <span>·</span>
              <span className="capitalize">{job.genre}</span>
            </>
          )}
        </div>

        {/* Progress bar */}
        <div className="w-full h-1 bg-starlight/10 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-purple-500 to-blue-500"
            initial={{ width: 0 }}
            animate={{ width: `${job.progress}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        </div>
      </div>

      <style>{`
        .shimmer-effect {
          background: linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.05) 50%, transparent 100%);
          animation: shimmer 2s infinite;
        }
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
      `}</style>
    </motion.div>
  );
}
