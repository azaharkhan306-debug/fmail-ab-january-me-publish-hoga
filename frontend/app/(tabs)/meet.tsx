import React, { useState } from "react";
import { View, Text, ScrollView, Pressable, RefreshControl } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { LinearGradient } from "expo-linear-gradient";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Button, Loading, ErrorState, Empty, Badge, Sheet, Field } from "@/src/ui";
import { Header } from "@/src/screen";
import { timeAgo } from "./mail";

const MODES = ["General", "Sales", "Customer Support", "Interview", "Classroom", "Team Standup", "Project Review", "Investor Meeting", "Product Demo", "Research Meeting"];

export default function Meet() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [mode, setMode] = useState("General");
  const [aiCopilot, setAiCopilot] = useState(true);

  const { data, isLoading, isError, refetch, isRefetching } = useQuery({ queryKey: ["meetings"], queryFn: () => api.get("/meetings") });

  const start = useMutation({
    mutationFn: (body: any) => api.post("/meetings", body),
    onSuccess: (m) => {
      qc.invalidateQueries({ queryKey: ["meetings"] });
      setOpen(false); setTitle("");
      router.push(`/meeting/${m.id}`);
    },
  });

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Fmail Meet" subtitle="Meetings with an AI copilot" showMenu showSearch={false} />
      {isLoading ? <Loading /> : isError ? <ErrorState onRetry={refetch} /> : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: 24 }}
          refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={colors.brandPrimary} />}>

          <LinearGradient colors={[colors.brandPrimary, colors.brandSecondary]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={{ borderRadius: radius.xl, padding: spacing.xl, marginBottom: spacing.lg }}>
            <Icon name="video-plus-outline" size={30} color="#fff" />
            <Text style={{ color: "#fff", fontSize: 20, fontWeight: "800", marginTop: 10 }}>Start an instant meeting</Text>
            <Text style={{ color: "#ffffffcc", fontSize: 14, marginTop: 4, marginBottom: 16 }}>AI copilot transcribes, captions & takes notes for you.</Text>
            <Pressable testID="new-meeting" onPress={() => setOpen(true)} style={{ backgroundColor: "#fff", borderRadius: radius.pill, paddingVertical: 12, alignItems: "center", flexDirection: "row", justifyContent: "center", gap: 8 }}>
              <Icon name="plus" size={20} color={colors.brandPrimary} />
              <Text style={{ color: colors.brandPrimary, fontWeight: "800", fontSize: 15 }}>New meeting</Text>
            </Pressable>
          </LinearGradient>

          <T size={17} weight="800" style={{ marginBottom: 10 }}>Recent meetings</T>
          {(data || []).length === 0 ? <Empty icon="video-outline" title="No meetings yet" subtitle="Start your first Fmail Meet." /> :
            (data || []).map((m: any) => (
              <Card key={m.id} testID={`meeting-${m.id}`} onPress={() => router.push(`/meeting/${m.id}`)} style={{ marginBottom: 10 }}>
                <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
                  <View style={{ width: 46, height: 46, borderRadius: 14, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" }}>
                    <Icon name={m.status === "active" ? "record-circle-outline" : "video-outline"} size={24} color={m.status === "active" ? colors.error : colors.brandPrimary} />
                  </View>
                  <View style={{ flex: 1 }}>
                    <T size={15} weight="700" numberOfLines={1}>{m.title}</T>
                    <T size={13} color={colors.muted}>{m.mode} · {timeAgo(m.created_at)} ago · {(m.attendees || []).length + 1} people</T>
                  </View>
                  {m.notes ? <Badge label="Notes ready" color={colors.success} /> : m.status === "active" ? <Badge label="Live" color={colors.error} tone="solid" /> : null}
                </View>
              </Card>
            ))}
        </ScrollView>
      )}

      <Sheet visible={open} onClose={() => setOpen(false)} title="New meeting" testID="new-meeting-sheet">
        <T size={13} weight="700" color={colors.muted} style={{ marginBottom: 6 }}>MEETING TITLE</T>
        <Field placeholder="e.g. Client proposal call" value={title} onChangeText={setTitle} testID="meeting-title-input" />
        <T size={13} weight="700" color={colors.muted} style={{ marginTop: 16, marginBottom: 8 }}>MEETING MODE</T>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {MODES.map((mo) => (
            <Pressable key={mo} onPress={() => setMode(mo)} style={{ paddingHorizontal: 14, height: 36, borderRadius: radius.pill, alignItems: "center", justifyContent: "center", backgroundColor: mode === mo ? colors.brandPrimary : colors.surfaceTertiary }}>
              <Text style={{ color: mode === mo ? "#fff" : colors.onSurfaceTertiary, fontWeight: "600", fontSize: 13 }}>{mo}</Text>
            </Pressable>
          ))}
        </View>
        <Pressable onPress={() => setAiCopilot(!aiCopilot)} style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 18, backgroundColor: colors.surfaceSecondary, padding: 14, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
            <Icon name="brain" size={20} color={colors.brandPrimary} />
            <Text style={{ color: colors.onSurface, fontWeight: "600" }}>Enable AI Copilot</Text>
          </View>
          <Icon name={aiCopilot ? "toggle-switch" : "toggle-switch-off-outline"} size={34} color={aiCopilot ? colors.brandPrimary : colors.muted} />
        </Pressable>
        <Button title="Start meeting" icon="video" testID="start-meeting-confirm" loading={start.isPending} onPress={() => start.mutate({ title: title || "Instant meeting", mode, aiCopilot })} style={{ marginTop: 20 }} />
      </Sheet>
    </View>
  );
}
