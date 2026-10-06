import React, { useState } from "react";
import { View, Text, ScrollView, Pressable, Alert } from "react-native";
import { Image } from "expo-image";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useTheme, spacing, radius } from "@/src/theme";
import { useAuth } from "@/src/auth";
import { Icon, Button, T } from "@/src/ui";

const FEATURES: { icon: any; title: string; sub: string }[] = [
  { icon: "email-fast-outline", title: "Your Gmail, supercharged", sub: "Connect Gmail and manage your real inbox" },
  { icon: "robot-happy-outline", title: "Ask Fmail", sub: "Your personal communication chief of staff" },
  { icon: "video-outline", title: "Fmail Meet", sub: "Meetings with an AI copilot, built in" },
  { icon: "brain", title: "Memory & Agents", sub: "It remembers, decides and acts for you" },
];

export default function Welcome() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { colors } = useTheme();
  const { loginWithGoogle } = useAuth();
  const [busy, setBusy] = useState(false);

  const onGoogle = async () => {
    setBusy(true);
    try {
      await loginWithGoogle();
      router.replace("/(tabs)");
    } catch (e: any) {
      Alert.alert("Google sign-in", e?.message || "Could not connect your Gmail. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <ScrollView contentContainerStyle={{ paddingTop: insets.top + 40, paddingBottom: insets.bottom + 24, paddingHorizontal: spacing.xl }}>
        <View style={{ alignItems: "center", marginBottom: 28 }}>
          <Image source={require("@/assets/images/icon.png")} style={{ width: 84, height: 84, borderRadius: 22 }} contentFit="cover" />
          <Text style={{ fontSize: 40, fontWeight: "900", color: colors.onSurface, marginTop: 18, letterSpacing: -1 }}>Fmail</Text>
          <Text style={{ fontSize: 16, color: colors.muted, marginTop: 6, textAlign: "center" }}>Your Gmail, with an AI assistant.</Text>
        </View>

        <View style={{ gap: 12, marginBottom: 32 }}>
          {FEATURES.map((f) => (
            <View key={f.title} style={{ flexDirection: "row", gap: 14, alignItems: "center", backgroundColor: colors.surfaceSecondary, padding: spacing.lg, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border }}>
              <View style={{ width: 46, height: 46, borderRadius: 14, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" }}>
                <Icon name={f.icon} size={24} color={colors.brandPrimary} />
              </View>
              <View style={{ flex: 1 }}>
                <T size={15} weight="700">{f.title}</T>
                <T size={13} color={colors.muted}>{f.sub}</T>
              </View>
            </View>
          ))}
        </View>

        <Button title="Continue with Google" icon="google" testID="welcome-google" loading={busy} onPress={onGoogle} />
        <Pressable onPress={() => router.push("/(auth)/login")} style={{ marginTop: 16, alignItems: "center" }} testID="welcome-login">
          <T color={colors.muted}>Sign in with email</T>
        </Pressable>
        <Pressable onPress={() => router.push("/terms")} style={{ marginTop: 18, alignItems: "center" }} testID="welcome-terms"><T size={12} color={colors.muted}>Terms & Conditions</T></Pressable>
        <Pressable onPress={() => router.push("/privacy")} style={{ marginTop: 8, alignItems: "center" }} testID="welcome-privacy"><T size={12} color={colors.muted}>Privacy Policy</T></Pressable>
      </ScrollView>
    </View>
  );
}
