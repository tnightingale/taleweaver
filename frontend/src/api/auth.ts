import type { User } from "../types";

const BASE = "/api/auth";

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
  return res.json();
}

export async function login(email: string, password: string): Promise<User> {
  const res = await fetch(`${BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = typeof err.detail === "string" ? err.detail : `Login failed: ${res.status}`;
    throw new Error(detail);
  }
  return res.json();
}

export async function logout(): Promise<void> {
  await fetch(`${BASE}/logout`, { method: "POST" });
}

export async function getCurrentUser(): Promise<User | null> {
  const res = await fetch(`${BASE}/me`);
  if (res.status === 401) return null;
  if (!res.ok) return null;
  return res.json();
}

export async function refreshToken(): Promise<boolean> {
  const res = await fetch(`${BASE}/refresh`, { method: "POST" });
  return res.ok;
}

export async function updateAccount(data: {
  display_name?: string;
  current_password?: string;
  new_password?: string;
}): Promise<User> {
  const res = await fetch(`${BASE}/me`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Update failed: ${res.status}`);
  }
  return res.json();
}

export function getGoogleAuthUrl(inviteCode?: string): string {
  const params = inviteCode ? `?invite=${encodeURIComponent(inviteCode)}` : "";
  return `${BASE}/google${params}`;
}
