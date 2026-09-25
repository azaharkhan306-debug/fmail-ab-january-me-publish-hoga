import React, { useState, useEffect } from "react";
import { View, Text, ScrollView, Pressable, ActivityIndicator } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Field, Empty, Avatar, Badge } from "@/src/ui";

export default function Search() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { colors } = useTheme();
  const [q, setQ] = useState("");
  const [res, setRes] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (q.trim().length < 2) { setRes(null); return; }
    const t = setTimeout(async () => {
      setLoading(true);
      try { setRes(await api.get("/search?q=" + encodeURIComponent(q))); } catch {} finally { setLoading(false); }
    }, 350);
    return () => clearTimeout(t);
  }, [q]);

  const total = res ? Object.values(res).reduce((s: number, arr: any) => s + arr.length, 0) : 0;

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <View style={{ paddingTop: insets.top + 8, paddingHorizontal: spacing.lg, paddingBottom: 10, flexDirection: "row", gap: 10, alignItems: "center" }}>
        <Pressable onPress={() => router.back()} testID="search-back"><Icon name="arrow-left" size={26} /></Pressable>
        <View style={{ flex: 1 }}>
          <Field icon="magnify" placeholder="Search everything…" value={q} onChangeText={setQ} testID="search-input" autoCapitalize="none" />
        </View>
      </View>
      <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 20, flexGrow: 1 }} keyboardShouldPersistTaps="handled">
        {loading ? <ActivityIndicator color={colors.brandPrimary} style={{ marginTop: 20 }} /> :
          !res ? <Empty icon="magnify" title="Universal search" subtitle="Search emails, people, meetings, tasks, files, memory and decisions." /> :
          total === 0 ? <Empty icon="magnify-close" title="No results" subtitle={`Nothing found for "${q}"`} /> :
          <>
            <Group title="Emails" icon="email-outline" items={res.emails} render={(e: any) => (
              <Pressable key={e.threadId} testID={`sr-email-${e.threadId}`} onPress={() => router.push(`/thread/${e.threadId}`)} style={{ flexDirection: "row", gap: 10, alignItems: "center", paddingVertical: 8 }}>
                <Avatar name={e.sender} size={36} />
                <View style={{ flex: 1 }}><T size={14} weight="700" numberOfLines={1}>{e.subject}</T><T size={12} color={colors.muted} numberOfLines={1}>{e.sender}</T></View>
              </Pressable>
            )} />
            <Group title="People" icon="account-outline" items={res.contacts} render={(c: any) => (
              <Pressable key={c.id} onPress={() => router.push("/contacts")} style={{ flexDirection: "row", gap: 10, alignItems: "center", paddingVertical: 8 }}>
                <Avatar name={c.name} size={36} /><View style={{ flex: 1 }}><T size={14} weight="700">{c.name}</T><T size={12} color={colors.muted}>{c.company}</T></View>
              </Pressable>
            )} />
            <Group title="Meetings" icon="video-outline" items={res.meetings} render={(m: any) => (
              <Pressable key={m.id} onPress={() => router.push(`/meeting/${m.id}`)} style={{ paddingVertical: 8 }}><T size={14} weight="600">{m.title}</T></Pressable>
            )} />
            <Group title="Tasks" icon="checkbox-marked-circle-outline" items={res.tasks} render={(t: any) => (
              <Pressable key={t.id} onPress={() => router.push("/tasks")} style={{ paddingVertical: 8 }}><T size={14} weight="600">{t.title}</T></Pressable>
            )} />
            <Group title="Memory" icon="brain" items={res.memory} render={(m: any) => (
              <Pressable key={m.id} onPress={() => router.push("/memory")} style={{ paddingVertical: 8 }}><T size={14} weight="600">{m.title}</T><T size={12} color={colors.muted}>{m.detail}</T></Pressable>
            )} />
            <Group title="Decisions" icon="gavel" items={res.decisions} render={(d: any) => (
              <View key={d.id} style={{ paddingVertical: 8 }}><T size={14} weight="600">{d.text}</T><T size={12} color={colors.muted}>{d.source}</T></View>
            )} />
          </>}
      </ScrollView>
    </View>
  );
}

function Group({ title, icon, items, render }: { title: string; icon: any; items: any[]; render: (x: any) => React.ReactNode }) {
  const { colors } = useTheme();
  if (!items?.length) return null;
  return (
    <View style={{ marginBottom: 14 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <Icon name={icon} size={16} color={colors.brandPrimary} />
        <T size={13} weight="800" color={colors.muted}>{title.toUpperCase()}</T>
        <Badge label={String(items.length)} tone="soft" />
      </View>
      <Card style={{ paddingVertical: 4 }}>{items.map(render)}</Card>
    </View>
  );
}
