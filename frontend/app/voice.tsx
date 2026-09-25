import React, { useState, useEffect } from "react";
import { View, Text, ScrollView, Pressable, Linking } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { AudioModule, RecordingPresets, setAudioModeAsync, useAudioRecorder, useAudioRecorderState } from "expo-audio";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Button, Field } from "@/src/ui";
import { Header } from "@/src/screen";

const LANGS = [{ k: "en-IN", l: "English", m: "transcribe" }, { k: "hi-IN", l: "Hindi", m: "transcribe" }, { k: "hi-IN", l: "Hinglish", m: "codemix" }];

export default function Voice() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const state = useAudioRecorderState(recorder);
  const [perm, setPerm] = useState<"unknown" | "granted" | "denied" | "blocked">("unknown");
  const [lang, setLang] = useState(LANGS[2]);
  const [text, setText] = useState("");
  const [xlate, setXlate] = useState("");

  useEffect(() => { (async () => { await setAudioModeAsync({ playsInSilentMode: true, allowsRecording: true }).catch(() => {}); })(); }, []);

  const askPerm = async () => {
    const res = await AudioModule.requestRecordingPermissionsAsync();
    if (res.granted) { setPerm("granted"); return true; }
    setPerm(res.canAskAgain ? "denied" : "blocked");
    return false;
  };

  const transcribe = useMutation({
    mutationFn: async (uri: string) => {
      const form = new FormData();
      form.append("file", { uri, name: "rec.m4a", type: "audio/mp4" } as any);
      form.append("language_code", lang.k);
      form.append("mode", lang.m);
      return api.upload("/voice/transcribe", form);
    },
    onSuccess: (r) => setText((t) => (t ? t + " " : "") + (r.transcript || "")),
  });

  const translate = useMutation({
    mutationFn: () => api.post("/translate", { text, source: lang.k === "hi-IN" ? "hi-IN" : "en-IN", target: lang.k === "hi-IN" ? "en-IN" : "hi-IN" }),
    onSuccess: (r) => setXlate(r.translated_text || ""),
  });

  const start = async () => {
    if (perm !== "granted") { const ok = await askPerm(); if (!ok) return; }
    await recorder.prepareToRecordAsync();
    recorder.record();
  };
  const stop = async () => {
    await recorder.stop();
    if (recorder.uri) transcribe.mutate(recorder.uri);
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Voice" subtitle="Dictate, ask & translate" back showSearch={false} />
      <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 20 }}>
        <View style={{ flexDirection: "row", gap: 8, marginBottom: 20 }}>
          {LANGS.map((l) => (
            <Pressable key={l.l} testID={`lang-${l.l.toLowerCase()}`} onPress={() => setLang(l)} style={{ flex: 1, paddingVertical: 12, borderRadius: radius.md, alignItems: "center", backgroundColor: lang.l === l.l ? colors.brandPrimary : colors.surfaceTertiary }}>
              <Text style={{ color: lang.l === l.l ? "#fff" : colors.onSurfaceTertiary, fontWeight: "700", fontSize: 13 }}>{l.l}</Text>
            </Pressable>
          ))}
        </View>

        <View style={{ alignItems: "center", marginBottom: 20 }}>
          <Pressable testID="record-button" onPress={state.isRecording ? stop : start}
            style={{ width: 100, height: 100, borderRadius: 50, backgroundColor: state.isRecording ? colors.error : colors.brandPrimary, alignItems: "center", justifyContent: "center", shadowColor: colors.brandPrimary, shadowOpacity: 0.4, shadowRadius: 16, elevation: 8 }}>
            <Icon name={state.isRecording ? "stop" : "microphone"} size={44} color="#fff" />
          </Pressable>
          <T size={14} color={colors.muted} style={{ marginTop: 14 }}>
            {transcribe.isPending ? "Transcribing…" : state.isRecording ? "Listening… tap to stop" : "Tap to dictate"}
          </T>
        </View>

        {perm === "denied" ? <Card style={{ marginBottom: 12 }}><T size={13} color={colors.muted} style={{ marginBottom: 8 }}>Microphone access is needed to dictate.</T><Button title="Allow microphone" small onPress={askPerm} testID="allow-mic" /></Card> : null}
        {perm === "blocked" ? <Card style={{ marginBottom: 12 }}><T size={13} color={colors.muted} style={{ marginBottom: 8 }}>Microphone is blocked. Enable it in Settings.</T><Button title="Open Settings" small variant="secondary" onPress={() => Linking.openSettings()} testID="open-settings" /></Card> : null}
        {transcribe.isError ? <Card style={{ marginBottom: 12 }}><T size={13} color={colors.error}>Transcription failed. Please try again.</T></Card> : null}

        <T size={13} weight="700" color={colors.muted} style={{ marginBottom: 6 }}>TRANSCRIPT</T>
        <Field placeholder="Your dictated text appears here…" value={text} onChangeText={setText} multiline testID="transcript-field" />

        {text ? (
          <>
            <View style={{ flexDirection: "row", gap: 8, marginTop: 14 }}>
              <Button title="Compose email" icon="email-outline" small style={{ flex: 1 }} testID="voice-compose" onPress={() => router.push({ pathname: "/compose" })} />
              <Button title="Translate" icon="translate" variant="secondary" small style={{ flex: 1 }} loading={translate.isPending} testID="voice-translate" onPress={() => translate.mutate()} />
            </View>
            {xlate ? (
              <Card style={{ marginTop: 14, backgroundColor: colors.brandTertiary, borderColor: colors.brandPrimary + "33" }}>
                <T size={11} weight="800" color={colors.onBrandTertiary} style={{ marginBottom: 4 }}>TRANSLATION</T>
                <T size={15} color={colors.onBrandTertiary}>{xlate}</T>
              </Card>
            ) : null}
          </>
        ) : null}
      </ScrollView>
    </View>
  );
}
