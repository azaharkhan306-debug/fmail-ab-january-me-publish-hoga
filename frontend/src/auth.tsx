import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { Platform } from "react-native";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import { api, setToken, clearToken, getToken } from "@/src/api";
import { storage } from "@/src/utils/storage";
import { track } from "@/src/analytics";
import { registerDeviceForPush } from "@/src/notifications";
import "@/src/firebase"; // ensure Firebase app is initialized app-wide

const USER_KEY = "fmail_user";

type User = {
  id: string; email: string; name: string;
  gmailConnected?: boolean; gmailEmail?: string | null;
  photo?: string | null; signature?: string; aliases?: string[];
  connectedAccounts?: any[]; aiEnabled?: boolean; memoryEnabled?: boolean; darkMode?: string;
};

type AuthCtx = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  signup: (email: string, password: string, name: string, code?: string) => Promise<void>;
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

  // Single-tap: Google sign-in that also connects the user's Gmail mailbox.
  const loginWithGoogle = async () => {
    const { url } = await api.get("/auth/google/login-url");
    const returnUrl = Linking.createURL("auth");
    const result = await WebBrowser.openAuthSessionAsync(url, returnUrl);
    if (result.type !== "success" || !result.url) {
      if (result.type === "cancel" || result.type === "dismiss") return;
      throw new Error("Google sign-in was cancelled.");
    }
    const parsed = Linking.parse(result.url);
    const code = (parsed.queryParams?.code as string) || "";
    const err = (parsed.queryParams?.error as string) || "";
    if (err) throw new Error("Google sign-in could not be completed. Please try again.");
    if (!code) throw new Error("Google sign-in did not return a code. Please try again.");
    const res = await api.post("/auth/google/exchange", { code });
    await setToken(res.token);
    setUser(res.user);
    try { await api.post("/gmail/sync"); } catch {}
    await track("login_google");
  };

  const signup = async (email: string, password: string, name: string, code?: string) => {
    const res = await api.post("/auth/signup", { email, password, name, code });
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
    <Ctx.Provider value={{ user, loading, login, loginWithGoogle, signup, logout, refresh, setUser }}>
      {children}
    </Ctx.Provider>
  );
}
