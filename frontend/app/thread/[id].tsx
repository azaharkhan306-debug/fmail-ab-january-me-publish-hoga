import React, { useState } from "react";
import { View, Text, ScrollView, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Button, Loading, ErrorState, Avatar, Badge, Sheet, Field } from "@/src/ui";
import { Header } from "@/src/screen";

const TONES = ["Professional", "Friendly", "Short", "Detailed", "Formal", "Casual", "Direct", "Diplomatic"];
const REWRITES: { key: string; label: string; icon: any }[] = [
  { key: "shorten", label: "Shorten", icon: "arrow-collapse-vertical" },
  { key: "expand", label: "Expand", icon: "arrow-expand-vertical" },
  { key: "grammar", label: "Fix grammar", icon: "spellcheck" },
  { key: "professional", label: "More pro", icon: "tie" },
  { key: "translate", label: "Translate", icon: "translate" },
];

export default function Thread() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"read" | "understand">("read");
  const [replyOpen, setReplyOpen] = useState(false);
  const [tone, setTone] = useState("Professional");
  const [draft, setDraft] = useState("");

  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["thread", id], queryFn: () => api.get(`/threads/${id}`) });
  const understand = useQuery({ queryKey: ["understand", id], queryFn: () => api.post(`/ai/understand/${id}`), enabled: tab === "understand" });
  const threadAI = useQuery({ queryKey: ["threadai", id], queryFn: () => api.post(`/ai/thread/${id}`), enabled: tab === "understand" });

  const patch = useMutation({
    mutationFn: (b: any) => api.patch(`/emails/${id}`, b),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["emails"] }); refetch(); },
  });
  const toTask = useMutation({
    mutationFn: () => api.post(`/ai/email-to-task/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["tasks"] }); router.push("/tasks"); },
  });
  const genReply = useMutation({
    mutationFn: (action: string) => api.post("/ai/reply", { threadId: id, tone, action, draft }),
    onSuccess: (r) => setDraft(r.text),
  });
  const sendReply = useMutation({
    mutationFn: () => api.post("/emails/compose", { to: data?.messages?.[0]?.senderEmail, subject: "Re: " + data?.subject, body: draft, threadId: id }),
    onSuccess: () => { setReplyOpen(false); setDraft(""); qc.invalidateQueries({ queryKey: ["emails"] }); refetch(); },
  });

  if (isLoading) return <View style={{ flex: 1, backgroundColor: colors.surface }}><Header title="Loading…" back showSearch={false} /><Loading /></View>;
  if (isError || !data) return <View style={{ flex: 1, backgroundColor: colors.surface }}><Header title="Error" back showSearch={false} /><ErrorState onRetry={refetch} /></View>;

  const last = data.messages[data.messages.length - 1];
  const u = understand.data;

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title={data.subject} back showSearch={false}
        right={
          <View style={{ flexDirection: "row", gap: 14 }}>
            <Pressable onPress={() => patch.mutate({ star: !last.star })} testID="thread-star"><Icon name={last.star ? "star" : "star-outline"} size={24} color={last.star ? "#C98A00" : colors.onSurface} /></Pressable>
            <Pressable onPress={() => { patch.mutate({ folder: "archive" }); router.back(); }} testID="thread-archive"><Icon name="archive-outline" size={24} /></Pressable>
            <Pressable onPress={() => { patch.mutate({ folder: "trash" }); router.back(); }} testID="thread-trash"><Icon name="trash-can-outline" size={24} /></Pressable>
          </View>
        } />

      <View style={{ flexDirection: "row", paddingHorizontal: spacing.lg, gap: 8, marginBottom: 8 }}>
        {(["read", "understand"] as const).map((t) => (
          <Pressable key={t} testID={`tab-${t}`} onPress={() => setTab(t)}
            style={{ flex: 1, paddingVertical: 10, borderRadius: radius.md, backgroundColor: tab === t ? colors.brandPrimary : colors.surfaceSecondary, alignItems: "center", flexDirection: "row", justifyContent: "center", gap: 6, borderWidth: 1, borderColor: tab === t ? colors.brandPrimary : colors.border }}>
            <Icon name={t === "read" ? "email-open-outline" : "brain"} size={17} color={tab === t ? "#fff" : colors.onSurface} />
            <Text style={{ color: tab === t ? "#fff" : colors.onSurface, fontWeight: "700", fontSize: 14 }}>{t === "read" ? "Conversation" : "AI Understanding"}</Text>
          </Pressable>
        ))}
      </View>

      <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 90 }}>
        {tab === "read" ? (
          <>
            {last.suspicious ? (
              <Card style={{ backgroundColor: "#D6454518", borderColor: "#D6454555", marginBottom: 12, flexDirection: "row", gap: 10, alignItems: "center" }}>
                <Icon name="shield-alert-outline" size={22} color={colors.error} />
                <T size={13} color={colors.error} style={{ flex: 1 }}>Fmail flagged this as possibly suspicious. Be cautious with links and requests.</T>
              </Card>
            ) : null}
            {data.messages.map((m: any) => (
              <Card key={m.id} style={{ marginBottom: 12 }}>
                <View style={{ flexDirection: "row", gap: 12, marginBottom: 12 }}>
                  <Avatar name={m.sender} size={44} />
                  <View style={{ flex: 1 }}>
                    <T size={15} weight="800">{m.sender}</T>
                    <T size={12} color={colors.muted}>{m.senderEmail}</T>
                    <T size={12} color={colors.muted}>to {m.to}</T>
                  </View>
                  <Badge label={m.aiLabel} />
                </View>
                <Text style={{ color: colors.onSurface, fontSize: 15, lineHeight: 23 }}>{m.body}</Text>
              </Card>
            ))}
          </>
        ) : (
          <>
            {understand.isLoading ? <Loading label="Fmail is understanding this email…" /> : u ? (
              <>
                <Card style={{ marginBottom: 12 }}>
                  <AIRow icon="target" label="Intent" value={u.intent} />
                  <AIRow icon="text-short" label="Topic" value={u.topic} />
                  <AIRow icon="gesture-tap" label="Requested action" value={u.requestedAction} />
                  <AIRow icon="clock-alert-outline" label="Deadline" value={u.deadline} last />
                </Card>
                {u.keyInfo?.length ? <InfoList title="Key information" icon="information-outline" items={u.keyInfo} /> : null}
                {u.questions?.length ? <InfoList title="Questions" icon="help-circle-outline" items={u.questions} /> : null}
                {u.commitments?.length ? <InfoList title="Commitments" icon="handshake-outline" items={u.commitments} /> : null}
                {u.people?.length ? (
                  <Card style={{ marginBottom: 12 }}>
                    <T size={13} weight="800" color={colors.muted} style={{ marginBottom: 8 }}>PEOPLE INVOLVED</T>
                    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
                      {u.people.map((p: string, i: number) => <View key={i} style={{ flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: colors.surfaceTertiary, paddingHorizontal: 10, paddingVertical: 6, borderRadius: radius.pill }}><Avatar name={p} size={22} /><Text style={{ color: colors.onSurface, fontSize: 13, fontWeight: "600" }}>{p}</Text></View>)}
                    </View>
                  </Card>
                ) : null}
                {threadAI.data?.nextAction ? (
                  <Card style={{ backgroundColor: colors.brandTertiary, borderColor: colors.brandPrimary + "44" }}>
                    <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 6 }}>
                      <Icon name="lightbulb-on-outline" size={18} color={colors.brandPrimary} />
                      <T size={13} weight="800" color={colors.onBrandTertiary}>RECOMMENDED NEXT ACTION</T>
                    </View>
                    <T size={15} weight="600" color={colors.onBrandTertiary}>{threadAI.data.nextAction}</T>
                  </Card>
                ) : null}
              </>
            ) : <ErrorState message="AI is unavailable right now." onRetry={understand.refetch} />}
          </>
        )}

        {/* Smart actions */}
        <T size={13} weight="800" color={colors.muted} style={{ marginTop: 16, marginBottom: 8 }}>SMART ACTIONS</T>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          <ActionChip icon="reply" label="AI Reply" onPress={() => setReplyOpen(true)} testID="action-reply" />
          <ActionChip icon="checkbox-marked-circle-plus-outline" label="To Task" onPress={() => toTask.mutate()} loading={toTask.isPending} testID="action-task" />
          <ActionChip icon="calendar-plus" label="Schedule Meeting" onPress={() => router.push({ pathname: "/calendar", params: { new: data.subject } })} testID="action-meeting" />
          <ActionChip icon="bell-plus-outline" label="Remind" onPress={() => toTask.mutate()} testID="action-remind" />
        </View>
      </ScrollView>

      <View style={{ position: "absolute", left: 0, right: 0, bottom: 0, padding: spacing.md, paddingBottom: insets.bottom + 8, backgroundColor: colors.surfaceSecondary, borderTopWidth: 1, borderTopColor: colors.border }}>
        <Button title="Write a reply with AI" icon="robot-happy-outline" testID="open-reply" onPress={() => setReplyOpen(true)} />
      </View>

      <Sheet visible={replyOpen} onClose={() => setReplyOpen(false)} title="AI Reply Writer" testID="reply-sheet">
        <T size={13} weight="700" color={colors.muted} style={{ marginBottom: 8 }}>TONE</T>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingBottom: 4 }} style={{ maxHeight: 46 }}>
          {TONES.map((t) => (
            <Pressable key={t} onPress={() => setTone(t)} style={{ height: 34, paddingHorizontal: 14, borderRadius: radius.pill, justifyContent: "center", backgroundColor: tone === t ? colors.brandPrimary : colors.surfaceTertiary }}>
              <Text style={{ color: tone === t ? "#fff" : colors.onSurfaceTertiary, fontWeight: "600", fontSize: 13 }}>{t}</Text>
            </Pressable>
          ))}
        </ScrollView>
        <Button title={draft ? "Regenerate reply" : "Generate reply"} icon="auto-fix" small testID="generate-reply" loading={genReply.isPending} onPress={() => genReply.mutate("reply")} style={{ marginTop: 12, alignSelf: "flex-start" }} />
        <View style={{ marginTop: 12 }}>
          <Field placeholder="Your reply will appear here. You can edit before sending." value={draft} onChangeText={setDraft} multiline testID="reply-draft" />
        </View>
        {draft ? (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingVertical: 12 }}>
            {REWRITES.map((r) => (
              <Pressable key={r.key} testID={`rewrite-${r.key}`} onPress={() => genReply.mutate(r.key)} style={{ flexDirection: "row", alignItems: "center", gap: 6, height: 34, paddingHorizontal: 12, borderRadius: radius.pill, backgroundColor: colors.surfaceTertiary }}>
                <Icon name={r.icon} size={15} color={colors.brandPrimary} />
                <Text style={{ color: colors.onSurfaceTertiary, fontWeight: "600", fontSize: 13 }}>{r.label}</Text>
              </Pressable>
            ))}
          </ScrollView>
        ) : null}
        <Button title="Send reply" icon="send" testID="send-reply" disabled={!draft.trim()} loading={sendReply.isPending} onPress={() => sendReply.mutate()} style={{ marginTop: 8 }} />
        <T size={12} color={colors.muted} style={{ textAlign: "center", marginTop: 10 }}>Fmail never sends without your explicit tap.</T>
      </Sheet>
    </View>
  );
}

function AIRow({ icon, label, value, last }: { icon: any; label: string; value?: string; last?: boolean }) {
  const { colors } = useTheme();
  return (
    <View style={{ flexDirection: "row", gap: 12, paddingVertical: 10, borderBottomWidth: last ? 0 : 1, borderBottomColor: colors.divider }}>
      <Icon name={icon} size={19} color={colors.brandPrimary} />
      <View style={{ flex: 1 }}>
        <T size={12} weight="700" color={colors.muted}>{label.toUpperCase()}</T>
        <T size={14} weight="500">{value || "—"}</T>
      </View>
    </View>
  );
}
function InfoList({ title, icon, items }: { title: string; icon: any; items: string[] }) {
  const { colors } = useTheme();
  return (
    <Card style={{ marginBottom: 12 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <Icon name={icon} size={17} color={colors.brandPrimary} />
        <T size={13} weight="800" color={colors.muted}>{title.toUpperCase()}</T>
      </View>
      {items.map((it, i) => (
        <View key={i} style={{ flexDirection: "row", gap: 8, marginBottom: 6 }}>
          <Text style={{ color: colors.brandPrimary }}>•</Text>
          <T size={14} style={{ flex: 1 }}>{it}</T>
        </View>
      ))}
    </Card>
  );
}
function ActionChip({ icon, label, onPress, loading, testID }: { icon: any; label: string; onPress: () => void; loading?: boolean; testID?: string }) {
  const { colors } = useTheme();
  return (
    <Pressable testID={testID} onPress={onPress} disabled={loading} style={{ flexDirection: "row", alignItems: "center", gap: 7, backgroundColor: colors.surfaceSecondary, paddingHorizontal: 14, paddingVertical: 11, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border }}>
      <Icon name={icon} size={18} color={colors.brandPrimary} />
      <Text style={{ color: colors.onSurface, fontWeight: "700", fontSize: 13 }}>{loading ? "Working…" : label}</Text>
    </Pressable>
  );
}
