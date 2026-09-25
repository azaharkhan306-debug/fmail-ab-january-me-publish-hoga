import { storage } from "@/src/utils/storage";

const BASE = process.env.EXPO_PUBLIC_BACKEND_URL + "/api";
const TOKEN_KEY = "fmail_token";

export async function getToken() {
  return storage.secureGet<string>(TOKEN_KEY, "");
}
export async function setToken(t: string) {
  return storage.secureSet(TOKEN_KEY, t);
}
export async function clearToken() {
  return storage.secureRemove(TOKEN_KEY);
}

async function req(path: string, opts: RequestInit = {}, timeoutMs = 60000): Promise<any> {
  const token = await getToken();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(BASE + path, {
      ...opts,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(opts.headers || {}),
      },
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) {
      throw new Error(data?.detail || "Something went wrong. Please try again.");
    }
    return data;
  } catch (e: any) {
    if (e.name === "AbortError") throw new Error("Request timed out. Check your connection.");
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  get: (p: string) => req(p),
  post: (p: string, body?: any) => req(p, { method: "POST", body: JSON.stringify(body ?? {}) }),
  put: (p: string, body?: any) => req(p, { method: "PUT", body: JSON.stringify(body ?? {}) }),
  patch: (p: string, body?: any) => req(p, { method: "PATCH", body: JSON.stringify(body ?? {}) }),
  del: (p: string) => req(p, { method: "DELETE" }),
  // multipart (voice)
  upload: async (p: string, form: FormData) => {
    const token = await getToken();
    const res = await fetch(BASE + p, {
      method: "POST",
      body: form,
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    });
    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) throw new Error(data?.detail || "Upload failed");
    return data;
  },
};
