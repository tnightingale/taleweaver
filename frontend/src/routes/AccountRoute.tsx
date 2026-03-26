import { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../contexts/AuthContext";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1, delayChildren: 0.15 } },
};
const item = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 260, damping: 20 } },
};

export default function AccountRoute() {
  const { user, updateUser } = useAuth();

  // Display name
  const [displayName, setDisplayName] = useState(user?.display_name || "");
  const [nameSuccess, setNameSuccess] = useState("");
  const [nameError, setNameError] = useState("");
  const [nameSaving, setNameSaving] = useState(false);

  // Password
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwSuccess, setPwSuccess] = useState("");
  const [pwError, setPwError] = useState("");
  const [pwSaving, setPwSaving] = useState(false);

  async function handleNameSubmit(e: React.FormEvent) {
    e.preventDefault();
    setNameError("");
    setNameSuccess("");
    setNameSaving(true);
    try {
      await updateUser({ display_name: displayName });
      setNameSuccess("Display name updated.");
    } catch (err: any) {
      setNameError(err.message || "Failed to update display name");
    } finally {
      setNameSaving(false);
    }
  }

  async function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPwError("");
    setPwSuccess("");

    if (newPassword !== confirmPassword) {
      setPwError("New passwords do not match");
      return;
    }

    setPwSaving(true);
    try {
      await updateUser({ current_password: currentPassword, new_password: newPassword });
      setPwSuccess("Password updated.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      setPwError(err.message || "Failed to update password");
    } finally {
      setPwSaving(false);
    }
  }

  return (
    <motion.div
      className="w-full max-w-md mx-auto px-4 py-12"
      variants={container}
      initial="hidden"
      animate="show"
    >
      <motion.div variants={item} className="flex items-center justify-between mb-8">
        <h1 className="font-display text-glow text-3xl text-starlight">
          Account
        </h1>
        <Link
          to="/"
          className="text-starlight/30 hover:text-starlight/60 text-sm transition-colors"
        >
          Back
        </Link>
      </motion.div>

      {/* Display name section */}
      <motion.div variants={item} className="mb-10">
        <h2 className="text-starlight/60 text-sm uppercase tracking-widest mb-4">
          Display name
        </h2>

        {nameSuccess && (
          <div className="mb-4 p-3 rounded-lg bg-green-500/10 border border-green-500/30 text-green-300 text-sm text-center">
            {nameSuccess}
          </div>
        )}
        {nameError && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm text-center">
            {nameError}
          </div>
        )}

        <form onSubmit={handleNameSubmit} className="space-y-4">
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Display name"
            required
            className="glow-input w-full"
          />
          <button
            type="submit"
            disabled={nameSaving || !displayName.trim() || displayName === user?.display_name}
            className="btn-glow w-full py-3 font-semibold disabled:opacity-40"
          >
            {nameSaving ? "Saving..." : "Update name"}
          </button>
        </form>
      </motion.div>

      {/* Divider */}
      <motion.div variants={item} className="flex items-center gap-4 mb-10">
        <div className="flex-1 h-px bg-starlight/10" />
      </motion.div>

      {/* Password section */}
      <motion.div variants={item}>
        <h2 className="text-starlight/60 text-sm uppercase tracking-widest mb-4">
          Change password
        </h2>

        {pwSuccess && (
          <div className="mb-4 p-3 rounded-lg bg-green-500/10 border border-green-500/30 text-green-300 text-sm text-center">
            {pwSuccess}
          </div>
        )}
        {pwError && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm text-center">
            {pwError}
          </div>
        )}

        <form onSubmit={handlePasswordSubmit} className="space-y-4">
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder="Current password"
            required
            className="glow-input w-full"
            autoComplete="current-password"
          />
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="New password"
            required
            minLength={8}
            className="glow-input w-full"
            autoComplete="new-password"
          />
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm new password"
            required
            minLength={8}
            className="glow-input w-full"
            autoComplete="new-password"
          />
          <button
            type="submit"
            disabled={pwSaving || !currentPassword || !newPassword || !confirmPassword}
            className="btn-glow w-full py-3 font-semibold disabled:opacity-40"
          >
            {pwSaving ? "Updating..." : "Change password"}
          </button>
        </form>
      </motion.div>
    </motion.div>
  );
}
