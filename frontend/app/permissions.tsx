import React, { useEffect, useState } from "react";
import { View, Text, ScrollView, Pressable, Alert, Linking, Platform } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useCameraPermissions, useMicrophonePermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card } from "@/src/ui";
import { Header } from "@/src/screen";

type Perm = {
  key: string; label: string; desc: string; icon: any; os?: boolean;
};

const PERMS: Perm[] = [
  { key: "camera", label: "Camera", desc: "For Fmail Meet video calls", icon: "camera-outline", os: true },
  { key: "microphone", label: "Microphone", desc: "For meetings and voice dictation", icon: "microphone-outline", os: true },
  { key: "storage", label: "Photos & files", desc: "Attach files and set your profile photo", icon: "image-outline", os: true },
  { key: "notifications", label: "Notifications", desc: "Alerts for important emails and follow-ups", icon: "bell-outline" },
  { key: "contacts", label: "Contacts", desc: "Suggest recipients from your address book", icon: "account-multiple-outline" },
];

export default function Permissions() {
  const insets = useSafeAreaInsets();
  const { user, setUser } = useAuth();
  const { colors } = useTheme();
  const [cam, requestCam] = useCameraPermissions();
  const [mic, requestMic] = useMicrophonePermissions();
  const [media, setMedia] = useState<boolean | null>(null);
  const [prefs, setPrefs] = useState<Record<string, boolean>>(user?.permissions || {});

  useEffect(() => {
    ImagePicker.getMediaLibraryPermissionsAsync().then((p) => setMedia(p.granted)).catch(() => setMedia(false));
  }, []);

  const savePref = async (key: string, val: boolean) => {
    const next = { ...prefs, [key]: val };
    setPrefs(next);
    try {
      const u = await api.put("/auth/permissions", { permissions: next });
      setUser(u);
    } catch (e: any) {
      Alert.alert("Fmail", e?.message || "Couldn't save your preference. Please try again.");
    }
  };

  const osGranted = (key: string) =>
    key === "camera" ? cam?.granted : key === "microphone" ? mic?.granted : key === "storage" ? media : false;

  const toggle = async (p: Perm, on: boolean) => {
    if (p.os) {
      if (on) {
        try {
          let granted = false;
          if (p.key === "camera") granted = (await requestCam()).granted;
          else if (p.key === "microphone") granted = (await requestMic()).granted;
          else if (p.key === "storage") granted = (await ImagePicker.requestMediaLibraryPermissionsAsync()).granted;
          if (p.key === "storage") setMedia(granted);
          if (!granted) {
            Alert.alert("Permission blocked", "Please enable this in your device Settings.",
              [{ text: "Cancel", style: "cancel" }, { text: "Open Settings", onPress: () => Linking.openSettings() }]);
            return;
          }
          await savePref(p.key, true);
        } catch {
          Alert.alert("Fmail", "Couldn't request that permission. Please try again.");
        }
      } else {
        Alert.alert("Turn off in Settings", `To revoke ${p.label} access, use your device Settings.`,
          [{ text: "Cancel", style: "cancel" }, { text: "Open Settings", onPress: () => Linking.openSettings() }]);
        await savePref(p.key, false);
      }
    } else {
      await savePref(p.key, on);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Permissions" back showSearch={false} />
      <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 20 }}>
        <T size={14} color={colors.muted} style={{ marginBottom: 14 }}>Control what Fmail can access. Changes apply immediately and are saved to your account.</T>
        <Card style={{ paddingVertical: 4 }}>
          {PERMS.map((p, i) => {
            const on = p.os ? !!osGranted(p.key) : !!prefs[p.key];
            return (
              <View key={p.key} style={{ flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 14, borderBottomWidth: i === PERMS.length - 1 ? 0 : 1, borderBottomColor: colors.divider }}>
                <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" }}>
                  <Icon name={p.icon} size={20} color={colors.brandPrimary} />
                </View>
                <View style={{ flex: 1 }}>
                  <T size={15} weight="700">{p.label}</T>
                  <T size={12} color={colors.muted}>{p.desc}</T>
                  <Text style={{ fontSize: 11, fontWeight: "700", marginTop: 3, color: on ? colors.success : colors.muted }}>
                    {p.os ? (on ? "Allowed" : "Not allowed") : (on ? "On" : "Off")}
                  </Text>
                </View>
                <Pressable testID={`perm-${p.key}`} onPress={() => toggle(p, !on)} hitSlop={8}>
                  <Icon name={on ? "toggle-switch" : "toggle-switch-off-outline"} size={40} color={on ? colors.brandPrimary : colors.muted} />
                </Pressable>
              </View>
            );
          })}
        </Card>
        {Platform.OS !== "web" ? (
          <T size={12} color={colors.muted} style={{ textAlign: "center", marginTop: 16 }}>
            System permissions (camera, microphone, photos) are managed by your device. Fmail requests them only when needed.
          </T>
        ) : null}
      </ScrollView>
    </View>
  );
}
