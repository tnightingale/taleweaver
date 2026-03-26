import type { User } from "../types";

const BASE = "/api/auth";
const USER_STORAGE_KEY = "tw-user";

function cacheUser(user: User): void {
  try {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  } catch {
    // localStorage may be unavailable (private browsing, quota exceeded)
  }
}

function clearCachedUser(): void {
  try {
    localStorage.removeItem(USER_STORAGE_KEY);
  } catch {
    // Ignore
  }
}

export function getCachedUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export async function signup(
  email: string,
  password: string,
  displayName: string,
  inviteCode: string,
): Promise<User> {
  const res = await fetch(`${BASE}/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password,
      display_name: displayName,
      invite_code: inviteCode,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Signup failed: ${res.status}`);
  }
  const user: User = await res.json();
  cacheUser(user);
  return user;
}

export async function login(email: string, password: string): Promise<User> {
  const res = await fetch(`${BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Login failed: ${res.status}`);
  }
  const user: User = await res.json();
  cacheUser(user);
  return user;
}

export async function logout(): Promise<void> {
  await fetch(`${BASE}/logout`, { method: "POST" });
  clearCachedUser();
}

export async function getCurrentUser(): Promise<User | null> {
  // navigator.onLine is unreliable on iOS (can return true in airplane mode),
  // so we also enforce a 3-second timeout to prevent the auth spinner from
  // hanging when the fetch can't complete.
  if (!navigator.onLine) return getCachedUser();

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    const res = await fetch(`${BASE}/me`, { signal: controller.signal });
    clearTimeout(timeout);
    if (res.status === 401) return null;
    if (!res.ok) return null;
    const user: User = await res.json();
    cacheUser(user);
    return user;
  } catch {
    // Network error or timeout — fall back to cached identity
    return getCachedUser();
  }
}

export async function refreshToken(): Promise<boolean> {
  const res = await fetch(`${BASE}/refresh`, { method: "POST" });
  return res.ok;
}

export function getGoogleAuthUrl(inviteCode?: string): string {
  const params = inviteCode ? `?invite=${encodeURIComponent(inviteCode)}` : "";
  return `${BASE}/google${params}`;
}
