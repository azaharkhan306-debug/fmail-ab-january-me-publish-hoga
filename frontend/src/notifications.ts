import { Platform } from "react-native";
import { router } from "expo-router";
import { api } from "@/src/api";

let backgroundRegistered = false;
let tapHandlersRegistered = false;

function messagingOrNull(): any {
  if (Platform.OS === "web") return null;
  try {
    return require("@react-native-firebase/messaging").default;
  } catch {
    return null;
  }
}

if (Platform.OS !== "web") {
  const messaging = messagingOrNull();
  if (messaging && !backgroundRegistered) {
    try {
      messaging().setBackgroundMessageHandler(async () => undefined);
      backgroundRegistered = true;
    } catch {}
  }
}

function routeToEmail(data: any) {
  const threadId = data?.threadId;
  if (threadId) {
    try { router.push(`/thread/${threadId}` as any); } catch {}
  } else {
    try { router.push("/(tabs)/mail" as any); } catch {}
  }
}

/** Open the right email when a notification is tapped (foreground, background, or cold start). */
export function setupNotificationTapHandling() {
  const messaging = messagingOrNull();
  if (!messaging || tapHandlersRegistered) return;
  tapHandlersRegistered = true;
  try {
    // App opened from background by tapping a notification.
    messaging().onNotificationOpenedApp((msg: any) => {
      if (msg?.data) routeToEmail(msg.data);
    });
    // App opened from a fully-quit state by tapping a notification.
    messaging().getInitialNotification().then((msg: any) => {
      if (msg?.data) setTimeout(() => routeToEmail(msg.data), 600);
    });
  } catch {}
}

export async function registerDeviceForPush() {
  if (Platform.OS === "web") return;
  const messaging = messagingOrNull();
  if (!messaging) return;
  try {
    const status = await messaging().requestPermission();
    const authorized = status === messaging.AuthorizationStatus.AUTHORIZED || status === messaging.AuthorizationStatus.PROVISIONAL;
    if (!authorized) return;
    const token = await messaging().getToken();
    if (token) await api.post("/push/register", { token, platform: Platform.OS });
    messaging().onTokenRefresh(async (next: string) => {
      try { await api.post("/push/register", { token: next, platform: Platform.OS }); } catch {}
    });
    setupNotificationTapHandling();
  } catch {}
}
