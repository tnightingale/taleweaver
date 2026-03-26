import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { User } from "../types";
import * as authApi from "../api/auth";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (
    email: string,
    password: string,
    displayName: string,
    inviteCode: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (data: {
    display_name?: string;
    current_password?: string;
    new_password?: string;
  }) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authApi
      .getCurrentUser()
      .then(setUser)
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const u = await authApi.login(email, password);
    setUser(u);
  }, []);

  const signup = useCallback(
    async (
      email: string,
      password: string,
      displayName: string,
      inviteCode: string,
    ) => {
      const u = await authApi.signup(email, password, displayName, inviteCode);
      setUser(u);
    },
    [],
  );

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
  }, []);

  const updateUser = useCallback(
    async (data: {
      display_name?: string;
      current_password?: string;
      new_password?: string;
    }) => {
      const u = await authApi.updateAccount(data);
      setUser(u);
    },
    [],
  );

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
