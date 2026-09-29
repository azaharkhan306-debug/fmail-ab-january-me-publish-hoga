import React, { useState } from "react";
import { View, Text, ScrollView, Pressable, Alert, Share } from "react-native";
import * as Clipboard from "expo-clipboard";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Button, Loading, ErrorState, Badge, Sheet, Field } from "@/src/ui";
import { Header } from "@/src/screen";

export default function Meeting() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const [inCall, setInCall] = useState<boolean | null>(null);
  const [mic, setMic] = useState(true);
  const [cam, setCam] = useState(true);
  const [captions, setCaptions] = useState(true);
  const [askOpen, setAskOpen] = useState(false);
  const [q, setQ] = useState("");
  const [ans, setAns] = useState("");
  const [meetingUrl, setMeetingUrl] = useState("");
  const [shareBusy, setShareBusy] = useState(false);

  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["meeting", id], queryFn: () => api.get(`/meetings/${id}`) });

  const shareMeeting = async () => {
    setShareBusy(true);
    try {
      const response = meetingUrl ? { url: meetingUrl } : await api.post(`/meetings/${id}/share`);
      setMeetingUrl(response.url);
      await Clipboard.setStringAsync(response.url);
      await Share.share({ message: `${data.title}: ${response.url}`, url: response.url });
    } catch (e: any) { Alert.alert("Fmail Meet", e?.message || "Could not share this meeting."); }
    finally { setShareBusy(false); }
  };

  const copyMeeting = async () => {
    setShareBusy(true);
    try { const response = meetingUrl ? { url: meetingUrl } : await api.post(`/meetings/${id}/share`); setMeetingUrl(response.url); await Clipboard.setStringAsync(response.url); Alert.alert("Meeting link copied", response.url); }
    catch (e: any) { Alert.alert("Fmail Meet", e?.message || "Could not copy this meeting link."); }
    finally { setShareBusy(false); }
  };

  const genNotes = useMutation({
    mutationFn: () => api.post(`/meetings/${id}/notes`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["meetings"] }); refetch(); },
  });
  const ask = useMutation({
    mutationFn: () => api.post(`/meetings/${id}/ask`, { question: q }),
    onSuccess: (r) => setAns(r.answer),
  });

  if (isLoading) return <View style={{ flex: 1, backgroundColor: colors.surface }}><Header title="Meeting" back showSearch={false} /><Loading /></View>;
  if (isError || !data) return <View style={{ flex: 1, backgroundColor: colors.surface }}><Header title="Meeting" back showSearch={false} /><ErrorState onRetry={refetch} /></View>;

  const live = inCall ?? (data.status === "active");
  const notes = data.notes;

  // In-call stage
  if (live && inCall !== false) {
    return (
      <View style={{ flex: 1, backgroundColor: "#0B0B0D" }}>
        <View style={{ paddingTop: insets.top + 10, paddingHorizontal: spacing.lg, flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
          <View>
            <Text style={{ color: "#fff", fontSize: 18, fontWeight: "800" }}>{data.title}</Text>
            <View style={{ flexDirection: "row", gap: 6, alignItems: "center", marginTop: 4 }}>
              <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: "#FF5E00" }} />
              <Text style={{ color: "#bbb", fontSize: 12 }}>{data.mode} · AI Copilot on</Text>
            </View>
          </View>
          <Pressable onPress={() => setInCall(false)}><Icon name="fullscreen-exit" size={26} color="#fff" /></Pressable>
        </View>

        <View style={{ flex: 1, padding: spacing.lg, gap: 12 }}>
          <View style={{ flex: 1, borderRadius: radius.xl, backgroundColor: "#17181B", alignItems: "center", justifyContent: "center" }}>
            {cam ? (
              <>
                <View style={{ width: 90, height: 90, borderRadius: 45, backgroundColor: "#FF5E00", alignItems: "center", justifyContent: "center" }}>
                  <Text style={{ color: "#fff", fontSize: 34, fontWeight: "800" }}>You</Text>
                </View>
                <Text style={{ color: "#fff", marginTop: 12, fontWeight: "600" }}>You</Text>
              </>
            ) : <Icon name="video-off-outline" size={40} color="#666" />}
          </View>
          {captions ? (
            <View style={{ backgroundColor: "#000000aa", borderRadius: radius.md, padding: 12 }}>
              <Text style={{ color: "#FF9A57", fontSize: 11, fontWeight: "800", marginBottom: 3 }}>LIVE CAPTIONS · EN</Text>
              <Text style={{ color: "#fff", fontSize: 15 }}>{data.transcript?.[0]?.text || "Listening… captions will appear here as people speak."}</Text>
            </View>
          ) : null}
        </View>

        {/* controls */}
        <View style={{ paddingBottom: insets.bottom + 16, paddingHorizontal: spacing.lg, flexDirection: "row", justifyContent: "space-around", alignItems: "center" }}>
          <CallBtn icon={mic ? "microphone" : "microphone-off"} on={mic} onPress={() => setMic(!mic)} testID="mic-toggle" />
          <CallBtn icon={cam ? "video" : "video-off"} on={cam} onPress={() => setCam(!cam)} testID="cam-toggle" />
          <CallBtn icon="monitor-share" on={false} onPress={() => {}} testID="screen-share" />
          <CallBtn icon="closed-caption-outline" on={captions} onPress={() => setCaptions(!captions)} testID="captions-toggle" />
          <Pressable testID="end-call" onPress={() => { setInCall(false); if (!notes) genNotes.mutate(); }}
            style={{ width: 60, height: 60, borderRadius: 30, backgroundColor: "#D64545", alignItems: "center", justifyContent: "center" }}>
            <Icon name="phone-hangup" size={28} color="#fff" />
          </Pressable>
        </View>
      </View>
    );
  }

  // Post-meeting / detail
  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title={data.title} subtitle={`${data.mode} · ${(data.attendees || []).length + 1} people`} back showSearch={false} />
      <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 20 }}>
        <View style={{ flexDirection: "row", gap: 10, marginBottom: 16 }}>
          <Button title="Share link" icon="share-variant" small variant="secondary" loading={shareBusy} onPress={shareMeeting} testID="share-meeting" style={{ flex: 1 }} />
          <Button title="Copy link" icon="content-copy" small variant="secondary" loading={shareBusy} onPress={copyMeeting} testID="copy-meeting" style={{ flex: 1 }} />
        </View>
        <View style={{ flexDirection: "row", gap: 10, marginBottom: 16 }}>
          <Button title="Rejoin" icon="video" small style={{ flex: 1 }} onPress={() => setInCall(true)} testID="rejoin" />
          <Button title="Ask Meeting" icon="robot-happy-outline" variant="secondary" small style={{ flex: 1 }} onPress={() => setAskOpen(true)} testID="ask-meeting" />
        </View>

        {!notes ? (
          <Card style={{ alignItems: "center", gap: 12, paddingVertical: 28 }}>
            <Icon name="text-box-check-outline" size={38} color={colors.brandPrimary} />
            <T size={16} weight="700">Generate AI meeting notes</T>
            <T size={13} color={colors.muted} style={{ textAlign: "center" }}>Summary, decisions, action items and follow-ups from the transcript.</T>
            <Button title="Generate with AI" icon="auto-fix" loading={genNotes.isPending} onPress={() => genNotes.mutate()} testID="gen-notes" />
          </Card>
        ) : (
          <>
            <Card style={{ marginBottom: 12, backgroundColor: colors.brandTertiary, borderColor: colors.brandPrimary + "33" }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 6 }}>
                <Icon name="text-box-outline" size={18} color={colors.brandPrimary} />
                <T size={13} weight="800" color={colors.onBrandTertiary}>SUMMARY</T>
              </View>
              <T size={15} color={colors.onBrandTertiary} style={{ lineHeight: 22 }}>{notes.summary}</T>
            </Card>
            <NotesList title="Key Points" icon="star-outline" items={notes.keyPoints} />
            <NotesList title="Decisions" icon="gavel" items={notes.decisions} />
            <NotesList title="Action Items" icon="checkbox-marked-circle-outline" items={notes.actionItems} />
            <NotesList title="Open Questions" icon="help-circle-outline" items={notes.questions} />
            <NotesList title="Next Steps" icon="arrow-right-circle-outline" items={notes.nextSteps} />
          </>
        )}

        {data.transcript?.length ? (
          <>
            <T size={17} weight="800" style={{ marginTop: 16, marginBottom: 8 }}>Transcript</T>
            <Card>
              {data.transcript.map((t: any, i: number) => (
                <View key={i} style={{ flexDirection: "row", gap: 10, paddingVertical: 8, borderBottomWidth: i === data.transcript.length - 1 ? 0 : 1, borderBottomColor: colors.divider }}>
                  <Text style={{ color: colors.muted, fontSize: 11, width: 40, paddingTop: 2 }}>{t.t}</Text>
                  <View style={{ flex: 1 }}>
                    <T size={13} weight="700" color={colors.brandPrimary}>{t.speaker}</T>
                    <T size={14}>{t.text}</T>
                  </View>
                </View>
              ))}
            </Card>
          </>
        ) : null}
      </ScrollView>

      <Sheet visible={askOpen} onClose={() => setAskOpen(false)} title="Ask this meeting" testID="ask-meeting-sheet">
        <Field placeholder="e.g. What did we decide about pricing?" value={q} onChangeText={setQ} multiline testID="ask-meeting-input" />
        <Button title="Ask" icon="send" small loading={ask.isPending} onPress={() => ask.mutate()} style={{ marginTop: 12, alignSelf: "flex-start" }} testID="ask-meeting-send" />
        {ans ? (
          <Card style={{ marginTop: 14, backgroundColor: colors.surfaceSecondary }}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 6 }}>
              <Icon name="brain" size={14} color={colors.brandPrimary} />
              <T size={11} weight="800" color={colors.brandPrimary}>FMAIL AI</T>
            </View>
            <T size={15} style={{ lineHeight: 22 }}>{ans}</T>
          </Card>
        ) : null}
      </Sheet>
    </View>
  );
}

function CallBtn({ icon, on, onPress, testID }: { icon: any; on: boolean; onPress: () => void; testID?: string }) {
  return (
    <Pressable testID={testID} onPress={onPress} style={{ width: 52, height: 52, borderRadius: 26, backgroundColor: on ? "#2A2C31" : "#fff", alignItems: "center", justifyContent: "center" }}>
      <Icon name={icon} size={24} color={on ? "#fff" : "#1C1C1E"} />
    </Pressable>
  );
}
function NotesList({ title, icon, items }: { title: string; icon: any; items?: string[] }) {
  const { colors } = useTheme();
  if (!items?.length) return null;
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
