import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, setToken, clearToken, getToken } from "@/src/api";
import { storage } from "@/src/utils/storage";
import { track } from "@/src/analytics";
import { registerDeviceForPush } from "@/src/notifications";
import "@/src/firebase"; // ensure Firebase app is initialized app-wide

const USER_KEY = "fmail_user";

type User = {
  id: string; email: string; name: string; handle: string; fmail: string;
  photo?: string | null; signature?: string; aliases?: string[];
  connectedAccounts?: any[]; aiEnabled?: boolean; memoryEnabled?: boolean; darkMode?: string;
};

type AuthCtx = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string, username: string, code?: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  setUser: (u: User) => void;
};

const Ctx = createContext<AuthCtx>(null as any);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const setUser = useCallback((u: User | null) => {
    setUserState(u);
    if (u) { storage.setItem(USER_KEY, JSON.stringify(u)); registerDeviceForPush(); }
    else storage.removeItem(USER_KEY);
  }, []);

  const bootstrap = useCallback(async () => {
    const token = await getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    // Instant open: hydrate cached user immediately, verify in background.
    const cached = await storage.getItem<string>(USER_KEY, "");
    if (cached) {
      try { setUserState(JSON.parse(cached)); } catch {}
      setLoading(false);
    }
    try {
      const me = await api.get("/auth/me");
      setUser(me);
    } catch {
      if (!cached) await clearToken();
    } finally {
      setLoading(false);
    }
  }, [setUser]);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const login = async (email: string, password: string) => {
    const res = await api.post("/auth/login", { email, password });
    await setToken(res.token);
    setUser(res.user);
    await track("login");
  };

  const signup = async (email: string, password: string, name: string, username: string, code?: string) => {
    const res = await api.post("/auth/signup", { email, password, name, username, code });
    await setToken(res.token);
    setUser(res.user);
    await track("signup");
  };

  const logout = async () => {
    await clearToken();
    setUser(null);
  };

  const refresh = async () => {
    try {
      const me = await api.get("/auth/me");
      setUser(me);
    } catch {}
  };

  return (
    <Ctx.Provider value={{ user, loading, login, signup, logout, refresh, setUser }}>
      {children}
    </Ctx.Provider>
  );
}
