import React, { useState } from "react";
import { View, Text, Pressable, Alert, ScrollView } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter, useLocalSearchParams } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as DocumentPicker from "expo-document-picker";
import * as FileSystem from "expo-file-system/legacy";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Button, Field, Sheet, Chip } from "@/src/ui";
import { Header } from "@/src/screen";

const TONES = ["Professional", "Friendly", "Short", "Detailed", "Formal", "Casual", "Direct", "Diplomatic"];

export default function Compose() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user } = useAuth();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const params = useLocalSearchParams<{ to?: string; subject?: string; body?: string; threadId?: string; draftId?: string }>();

  const [to, setTo] = useState(params.to || "");
  const [cc, setCc] = useState("");
  const [bcc, setBcc] = useState("");
  const [showCc, setShowCc] = useState(false);
  const [subject, setSubject] = useState(params.subject || "");
  const [body, setBody] = useState(params.body || "");
  const [attachments, setAttachments] = useState<any[]>([]);
  const [err, setErr] = useState("");

  // AI writer state
  const [aiOpen, setAiOpen] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [tone, setTone] = useState("Professional");
  const [preview, setPreview] = useState<{ subject: string; body: string } | null>(null);

  const send = useMutation({
    mutationFn: (draft: boolean) => api.post("/emails/compose", {
      to, cc, bcc, subject,
      body: body + (user?.signature && !draft ? "\n\n" + user.signature : ""),
      attachments, threadId: params.threadId, draftId: params.draftId, draft,
    }),
    onSuccess: (_d, draft) => {
      qc.invalidateQueries({ queryKey: ["emails"] });
      Alert.alert("Fmail", draft ? "Draft saved." : "Email sent.");
      router.back();
    },
    onError: (e: any) => setErr(e?.message || "Couldn't send. Please try again."),
  });

  const generate = useMutation({
    mutationFn: () => api.post("/ai/compose", { instruction, tone, to, context: body }),
    onSuccess: (d: any) => setPreview({ subject: d.subject, body: d.body }),
    onError: (e: any) => setErr(e?.message || "AI could not generate. Please try again."),
  });

  const onSend = () => {
    setErr("");
    if (!to.trim()) return setErr("Please add a recipient.");
    if (!subject.trim()) return setErr("Please add a subject.");
    send.mutate(false);
  };

  const pickAttachment = async () => {
    try {
      const res = await DocumentPicker.getDocumentAsync({ copyToCacheDirectory: true, multiple: false });
      if (res.canceled || !res.assets?.length) return;
      const a = res.assets[0];
      if ((a.size || 0) > 4 * 1024 * 1024) {
        return Alert.alert("Attachment too large", "Please choose a file under 4 MB.");
      }
      const data = await FileSystem.readAsStringAsync(a.uri, { encoding: "base64" });
      setAttachments((prev) => [...prev, { name: a.name, type: a.mimeType || "file", size: String(a.size || 0), data }]);
    } catch {
      Alert.alert("Fmail", "Couldn't attach that file. Please try again.");
    }
  };

  const insertAI = () => {
    if (!preview) return;
    if (!subject.trim()) setSubject(preview.subject);
    setBody((b) => (b.trim() ? b + "\n\n" + preview.body : preview.body));
    setPreview(null);
    setInstruction("");
    setAiOpen(false);
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title={params.threadId ? "Reply" : "Compose"} back showSearch={false}
        right={<Pressable onPress={() => send.mutate(true)} testID="save-draft"><T color={colors.brandPrimary} weight="700">Save draft</T></Pressable>} />
      <KeyboardAwareScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 40 }} bottomOffset={24} keyboardShouldPersistTaps="handled">
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.divider }}>
          <Icon name="at" size={18} color={colors.brandPrimary} />
          <T size={13} color={colors.muted}>From</T>
          <T size={14} weight="600">{user?.fmail}</T>
        </View>

        <View style={{ gap: 12, marginTop: 14 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
            <View style={{ flex: 1 }}>
              <Field icon="account-outline" placeholder="To" value={to} onChangeText={setTo} autoCapitalize="none" keyboardType="email-address" testID="compose-to" />
            </View>
            <Pressable onPress={() => setShowCc((v) => !v)} testID="toggle-cc" hitSlop={8}>
              <T size={13} weight="700" color={colors.brandPrimary}>{showCc ? "Hide" : "Cc/Bcc"}</T>
            </Pressable>
          </View>
          {showCc ? (
            <>
              <Field icon="account-multiple-outline" placeholder="Cc" value={cc} onChangeText={setCc} autoCapitalize="none" keyboardType="email-address" testID="compose-cc" />
              <Field icon="account-multiple-outline" placeholder="Bcc" value={bcc} onChangeText={setBcc} autoCapitalize="none" keyboardType="email-address" testID="compose-bcc" />
            </>
          ) : null}
          <Field icon="format-title" placeholder="Subject" value={subject} onChangeText={setSubject} testID="compose-subject" />
          <Field placeholder="Write your message…" value={body} onChangeText={setBody} multiline testID="compose-body" style={{ minHeight: 200 }} />
        </View>

        {attachments.length ? (
          <View style={{ gap: 8, marginTop: 12 }}>
            {attachments.map((a, i) => (
              <View key={i} style={{ flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: colors.surfaceSecondary, borderRadius: radius.md, padding: 12, borderWidth: 1, borderColor: colors.border }}>
                <Icon name="paperclip" size={18} color={colors.brandPrimary} />
                <T size={13} style={{ flex: 1 }} numberOfLines={1}>{a.name}</T>
                <Pressable onPress={() => setAttachments((p) => p.filter((_, j) => j !== i))} hitSlop={8} testID={`remove-attach-${i}`}>
                  <Icon name="close-circle" size={18} color={colors.muted} />
                </Pressable>
              </View>
            ))}
          </View>
        ) : null}

        {err ? <Text style={{ color: colors.error, marginTop: 12 }}>{err}</Text> : null}

        <View style={{ flexDirection: "row", gap: 10, marginTop: 18 }}>
          <Button title="AI Writer" icon="creation" variant="secondary" testID="open-ai-writer" onPress={() => setAiOpen(true)} style={{ flex: 1 }} />
          <Button title="Attach" icon="paperclip" variant="secondary" testID="attach-file" onPress={pickAttachment} style={{ flex: 1 }} />
        </View>
        <Button title="Send email" icon="send" testID="compose-send" loading={send.isPending} onPress={onSend} style={{ marginTop: 12 }} />
      </KeyboardAwareScrollView>

      <Sheet visible={aiOpen} onClose={() => setAiOpen(false)} title="AI Email Writer" testID="ai-writer-sheet">
        <T size={13} weight="700" color={colors.muted} style={{ marginBottom: 6 }}>WHAT SHOULD THE EMAIL SAY?</T>
        <Field placeholder="e.g. Ask Rahul to reschedule our call to Friday 3pm" value={instruction} onChangeText={setInstruction} multiline testID="ai-instruction" style={{ minHeight: 80 }} />
        <T size={13} weight="700" color={colors.muted} style={{ marginTop: 16, marginBottom: 8 }}>TONE</T>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingBottom: 4 }}>
          {TONES.map((t) => <Chip key={t} label={t} active={tone === t} onPress={() => setTone(t)} testID={`tone-${t}`} />)}
        </ScrollView>

        <Button title={preview ? "Regenerate" : "Generate email"} icon={preview ? "refresh" : "creation"} testID="ai-generate"
          loading={generate.isPending} onPress={() => generate.mutate()} style={{ marginTop: 16 }}
          disabled={!instruction.trim()} />

        {preview ? (
          <View style={{ marginTop: 16 }}>
            <T size={13} weight="700" color={colors.muted} style={{ marginBottom: 6 }}>PREVIEW (editable)</T>
            <Field placeholder="Subject" value={preview.subject} onChangeText={(v: string) => setPreview({ ...preview, subject: v })} testID="ai-preview-subject" />
            <View style={{ height: 10 }} />
            <Field placeholder="Body" value={preview.body} onChangeText={(v: string) => setPreview({ ...preview, body: v })} multiline testID="ai-preview-body" style={{ minHeight: 160 }} />
            <View style={{ flexDirection: "row", gap: 10, marginTop: 14 }}>
              <Button title="Cancel" variant="ghost" testID="ai-cancel" onPress={() => setPreview(null)} style={{ flex: 1 }} />
              <Button title="Insert into email" icon="check" testID="ai-insert" onPress={insertAI} style={{ flex: 2 }} />
            </View>
            <T size={12} color={colors.muted} style={{ textAlign: "center", marginTop: 10 }}>AI drafts are never sent automatically. Review before sending.</T>
          </View>
        ) : null}
      </Sheet>
    </View>
  );
}
