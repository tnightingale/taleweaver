import { useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth } from "../contexts/AuthContext";
import { getGoogleAuthUrl } from "../api/auth";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1, delayChildren: 0.15 } },
};
const item = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 260, damping: 20 } },
};

export default function SignupRoute() {
  const { user, signup } = useAuth();
  const [searchParams] = useSearchParams();
  const inviteCode = searchParams.get("invite") || "";

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  if (!inviteCode) {
    return (
      <motion.div
        className="w-full max-w-md mx-auto px-4 py-12 text-center"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="font-display text-glow text-4xl mb-6 text-starlight">
          Invite required
        </h1>
        <p className="text-starlight/50 mb-8">
          You need an invite link to create an account. Ask someone who already has access to send you one.
        </p>
        <Link to="/login" className="text-gold-light hover:text-gold-light/80 transition-colors">
          Already have an account? Sign in
        </Link>
      </motion.div>
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setSubmitting(true);
    try {
      await signup(email, password, displayName, inviteCode);
    } catch (err: any) {
      setError(err.message || "Signup failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <motion.div
      className="w-full max-w-md mx-auto px-4 py-12"
      variants={container}
      initial="hidden"
      animate="show"
    >
      <motion.h1
        variants={item}
        className="font-display text-glow text-4xl text-center mb-8 text-starlight"
      >
        Create your account
      </motion.h1>

      {error && (
        <motion.div variants={item} className="mb-6 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm text-center">
          {error}
        </motion.div>
      )}

      <motion.form variants={item} onSubmit={handleSubmit} className="space-y-5">
        <div>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Your name"
            required
            className="glow-input w-full"
            autoComplete="name"
          />
        </div>
        <div>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
            className="glow-input w-full"
            autoComplete="email"
          />
        </div>
        <div>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password (min 8 characters)"
            required
            minLength={8}
            className="glow-input w-full"
            autoComplete="new-password"
          />
        </div>
        <button
          type="submit"
          disabled={submitting || !displayName || !email || !password}
          className="btn-glow w-full py-3 text-lg font-semibold disabled:opacity-40"
        >
          {submitting ? "Creating account..." : "Create account"}
        </button>
      </motion.form>

      <motion.div variants={item} className="mt-6 flex items-center gap-4">
        <div className="flex-1 h-px bg-starlight/10" />
        <span className="text-starlight/30 text-sm">or</span>
        <div className="flex-1 h-px bg-starlight/10" />
      </motion.div>

      <motion.div variants={item} className="mt-6">
        <a
          href={getGoogleAuthUrl(inviteCode)}
          className="glass-card flex items-center justify-center gap-3 w-full py-3 text-starlight/70 hover:text-starlight transition-colors"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path
              fill="currentColor"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
            />
            <path
              fill="currentColor"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="currentColor"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="currentColor"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          Sign up with Google
        </a>
      </motion.div>

      <motion.p variants={item} className="mt-8 text-center text-starlight/40 text-sm">
        Already have an account?{" "}
        <Link to="/login" className="text-gold-light hover:text-gold-light/80 transition-colors">
          Sign in
        </Link>
      </motion.p>
    </motion.div>
  );
}
