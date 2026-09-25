import React from "react";
import { View, Text, ScrollView } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { LinearGradient } from "expo-linear-gradient";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, Button, T } from "@/src/ui";

const FEATURES: { icon: any; title: string; sub: string }[] = [
  { icon: "email-fast-outline", title: "Universal AI Inbox", sub: "All your accounts, understood automatically" },
  { icon: "robot-happy-outline", title: "Ask Fmail", sub: "Your personal communication chief of staff" },
  { icon: "video-outline", title: "Fmail Meet", sub: "Meetings with an AI copilot, built in" },
  { icon: "brain", title: "Memory & Agents", sub: "It remembers, decides and acts for you" },
];

export default function Welcome() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { colors } = useTheme();
  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <ScrollView contentContainerStyle={{ paddingTop: insets.top + 40, paddingBottom: insets.bottom + 24, paddingHorizontal: spacing.xl }}>
        <View style={{ alignItems: "center", marginBottom: 28 }}>
          <LinearGradient colors={[colors.brandPrimary, colors.brandSecondary]} style={{ width: 76, height: 76, borderRadius: 22, alignItems: "center", justifyContent: "center" }}>
            <Icon name="at" size={44} color="#fff" />
          </LinearGradient>
          <Text style={{ fontSize: 40, fontWeight: "900", color: colors.onSurface, marginTop: 18, letterSpacing: -1 }}>Fmail</Text>
          <Text style={{ fontSize: 16, color: colors.muted, marginTop: 6, textAlign: "center" }}>Your Communication. Your Intelligence. Your AI.</Text>
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

        <Button title="Create your Fmail identity" icon="rocket-launch-outline" testID="welcome-signup" onPress={() => router.push("/(auth)/signup")} />
        <Button title="I already have an account" variant="ghost" testID="welcome-login" onPress={() => router.push("/(auth)/login")} style={{ marginTop: 8 }} />
      </ScrollView>
    </View>
  );
}
