import { Platform } from "react-native";
import { api } from "@/src/api";

let backgroundRegistered = false;
if (Platform.OS !== "web") {
  try {
    const messaging = require("@react-native-firebase/messaging").default;
    if (!backgroundRegistered) {
      messaging().setBackgroundMessageHandler(async () => undefined);
      backgroundRegistered = true;
    }
  } catch {}
}

export async function registerDeviceForPush() {
  if (Platform.OS === "web") return;
  try {
    const messaging = require("@react-native-firebase/messaging").default;
    const status = await messaging().requestPermission();
    const authorized = status === messaging.AuthorizationStatus.AUTHORIZED || status === messaging.AuthorizationStatus.PROVISIONAL;
    if (!authorized) return;
    const token = await messaging().getToken();
    if (token) await api.post("/push/register", { token, platform: Platform.OS });
    messaging().onTokenRefresh(async (next: string) => {
      try { await api.post("/push/register", { token: next, platform: Platform.OS }); } catch {}
    });
  } catch {}
}
