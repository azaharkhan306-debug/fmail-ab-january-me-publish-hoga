import React from "react";
import { View, Text, ScrollView, Pressable, RefreshControl } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { LinearGradient } from "expo-linear-gradient";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, Card, T, Loading, ErrorState, Avatar, Badge } from "@/src/ui";
import { Header } from "@/src/screen";

const HUB: { icon: any; label: string; route: string; color: string }[] = [
  { icon: "calendar-month-outline", label: "Calendar", route: "/calendar", color: "#2F6FED" },
  { icon: "checkbox-marked-circle-outline", label: "Tasks", route: "/tasks", color: "#1E9E5A" },
  { icon: "folder-outline", label: "Files", route: "/files", color: "#C98A00" },
  { icon: "account-group-outline", label: "Contacts", route: "/contacts", color: "#9A6BFF" },
  { icon: "brain", label: "Memory", route: "/memory", color: "#FF5E00" },
  { icon: "apps", label: "Agents", route: "/agents", color: "#D64545" },
  { icon: "shape-outline", label: "Spaces", route: "/spaces", color: "#00A6A6" },
  { icon: "shield-account-outline", label: "AI Rep", route: "/representative", color: "#FF6600" },
];

const QUICK: { icon: any; label: string; route: string }[] = [
  { icon: "pencil-outline", label: "Compose", route: "/compose" },
  { icon: "video-plus-outline", label: "Meet", route: "/(tabs)/meet" },
  { icon: "robot-happy-outline", label: "Ask", route: "/(tabs)/ask" },
  { icon: "microphone-outline", label: "Voice", route: "/voice" },
];

export default function Home() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user } = useAuth();
  const { colors } = useTheme();
  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api.get("/dashboard"),
  });

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Fmail" subtitle={user?.gmailEmail || user?.email} showMenu showSearch />
      {isLoading ? <Loading /> : isError ? <ErrorState onRetry={refetch} /> : (
        <ScrollView
          contentContainerStyle={{ paddingHorizontal: spacing.lg, paddingBottom: 24 }}
          refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={colors.brandPrimary} />}
        >
          {/* AI Brief */}
          <Pressable onPress={() => router.push("/(tabs)/ask")} testID="daily-brief">
            <LinearGradient colors={[colors.brandPrimary, colors.brandSecondary]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
              style={{ borderRadius: radius.xl, padding: spacing.xl, marginBottom: spacing.lg }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <Icon name="brain" size={18} color="#fff" />
                <Text style={{ color: "#fff", fontWeight: "800", fontSize: 13, letterSpacing: 0.3 }}>FMAIL DAILY BRIEF</Text>
              </View>
              <Text style={{ color: "#fff", fontSize: 18, fontWeight: "700", lineHeight: 25 }}>{data?.brief}</Text>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 6, marginTop: 14 }}>
                <Text style={{ color: "#ffffffcc", fontWeight: "600", fontSize: 13 }}>Ask Fmail anything</Text>
                <Icon name="arrow-right" size={16} color="#ffffffcc" />
              </View>
            </LinearGradient>
          </Pressable>

          {/* Quick actions */}
          <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: spacing.lg }}>
            {QUICK.map((q) => (
              <Pressable key={q.label} onPress={() => router.push(q.route as any)} testID={`quick-${q.label.toLowerCase()}`}
                style={{ alignItems: "center", gap: 6, flex: 1 }}>
                <View style={{ width: 56, height: 56, borderRadius: 18, backgroundColor: colors.surfaceSecondary, borderWidth: 1, borderColor: colors.border, alignItems: "center", justifyContent: "center" }}>
                  <Icon name={q.icon} size={24} color={colors.brandPrimary} />
                </View>
                <Text style={{ fontSize: 12, color: colors.onSurfaceTertiary, fontWeight: "600" }}>{q.label}</Text>
              </Pressable>
            ))}
          </View>

          {/* Stat strip */}
          <View style={{ flexDirection: "row", gap: 10, marginBottom: spacing.lg }}>
            <Stat label="Urgent" value={data?.counts?.urgent} color="#D64545" onPress={() => router.push("/(tabs)/mail")} />
            <Stat label="Waiting" value={data?.counts?.waiting} color="#C98A00" onPress={() => router.push("/followups")} />
            <Stat label="Tasks" value={data?.counts?.tasks} color="#1E9E5A" onPress={() => router.push("/tasks")} />
          </View>

          {/* Needs action */}
          <Section title="Needs Action" onSeeAll={() => router.push("/(tabs)/mail")}>
            {(data?.needsAction || []).length === 0 ? (
              <T color={colors.muted}>{"You're all caught up. Nice work."}</T>
            ) : data.needsAction.map((e: any) => (
              <Pressable key={e.threadId} onPress={() => router.push(`/thread/${e.threadId}`)} testID={`action-${e.threadId}`}
                style={{ flexDirection: "row", gap: 12, alignItems: "center", paddingVertical: 10 }}>
                <Avatar name={e.sender} size={40} />
                <View style={{ flex: 1 }}>
                  <T size={14} weight="700" numberOfLines={1}>{e.sender}</T>
                  <T size={13} color={colors.muted} numberOfLines={1}>{e.subject}</T>
                </View>
                <Badge label={e.aiLabel} />
              </Pressable>
            ))}
          </Section>

          {/* Today meetings */}
          <Section title="Today's Meetings" onSeeAll={() => router.push("/calendar")}>
            {(data?.todayMeetings || []).slice(0, 3).map((ev: any) => (
              <Pressable key={ev.id} onPress={() => router.push("/calendar")} style={{ flexDirection: "row", gap: 12, alignItems: "center", paddingVertical: 10 }}>
                <View style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" }}>
                  <Icon name="video-outline" size={20} color={colors.brandPrimary} />
                </View>
                <View style={{ flex: 1 }}>
                  <T size={14} weight="700" numberOfLines={1}>{ev.title}</T>
                  <T size={13} color={colors.muted}>{new Date(ev.start).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" })}</T>
                </View>
                <Icon name="chevron-right" size={22} color={colors.muted} />
              </Pressable>
            ))}
          </Section>

          {/* Hub grid */}
          <T size={17} weight="800" style={{ marginBottom: 12, marginTop: 4 }}>Everything, in one place</T>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
            {HUB.map((h) => (
              <Pressable key={h.label} onPress={() => router.push(h.route as any)} testID={`hub-${h.label.toLowerCase().replace(" ", "-")}`}
                style={{ width: "23%", alignItems: "center", gap: 6, paddingVertical: 12, backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border }}>
                <View style={{ width: 42, height: 42, borderRadius: 13, backgroundColor: h.color + "1E", alignItems: "center", justifyContent: "center" }}>
                  <Icon name={h.icon} size={22} color={h.color} />
                </View>
                <Text style={{ fontSize: 11, color: colors.onSurfaceTertiary, fontWeight: "600" }}>{h.label}</Text>
              </Pressable>
            ))}
          </View>
        </ScrollView>
      )}
    </View>
  );
}

function Stat({ label, value, color, onPress }: { label: string; value?: number; color: string; onPress: () => void }) {
  const { colors } = useTheme();
  return (
    <Pressable onPress={onPress} style={{ flex: 1, backgroundColor: colors.surfaceSecondary, borderRadius: radius.lg, padding: spacing.md, borderWidth: 1, borderColor: colors.border }}>
      <Text style={{ fontSize: 26, fontWeight: "900", color }}>{value ?? 0}</Text>
      <Text style={{ fontSize: 12, color: colors.muted, fontWeight: "600" }}>{label}</Text>
    </Pressable>
  );
}

function Section({ title, children, onSeeAll }: { title: string; children: React.ReactNode; onSeeAll?: () => void }) {
  const { colors } = useTheme();
  return (
    <View style={{ marginBottom: spacing.lg }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <T size={17} weight="800">{title}</T>
        {onSeeAll ? <Pressable onPress={onSeeAll}><Text style={{ color: colors.brandPrimary, fontWeight: "700", fontSize: 13 }}>See all</Text></Pressable> : null}
      </View>
      <Card style={{ paddingVertical: 4 }}>{children}</Card>
    </View>
  );
}
