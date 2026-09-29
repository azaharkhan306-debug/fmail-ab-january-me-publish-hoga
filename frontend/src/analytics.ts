import { Platform } from "react-native";
import { api } from "@/src/api";

const scrub = (params: Record<string, unknown> = {}) => Object.fromEntries(
  Object.entries(params).filter(([key]) => !/email|body|content|message|token/i.test(key)).map(([key, value]) => [key, String(value).slice(0, 120)]),
);

export async function track(name: string, params: Record<string, unknown> = {}) {
  const safe = scrub(params);
  try {
    if (Platform.OS === "web") {
      const analytics = await import("firebase/analytics");
      if (await analytics.isSupported()) await analytics.logEvent(analytics.getAnalytics(), name, safe as Record<string, any>);
    } else {
      const nativeAnalytics = require("@react-native-firebase/analytics").default;
      await nativeAnalytics().logEvent(name, safe);
    }
  } catch {}
  try { await api.post("/analytics", { name, params: safe }); } catch {}
}
