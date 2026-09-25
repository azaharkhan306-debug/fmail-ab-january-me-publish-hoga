import React, { useState, useRef } from "react";
import { View, Text, ScrollView, Pressable, ActivityIndicator } from "react-native";
import { KeyboardAvoidingView, KeyboardStickyView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Field } from "@/src/ui";
import { Header } from "@/src/screen";

const SUGGESTIONS = [
  "What emails need my attention?",
  "Summarize my unread emails",
  "Who am I waiting for?",
  "What payments are due?",
  "What meetings do I have tomorrow?",
  "What did I promise to do?",
];

export default function Ask() {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const [input, setInput] = useState("");
  const scrollRef = useRef<ScrollView>(null);

  const { data: history } = useQuery({ queryKey: ["chat-history"], queryFn: () => api.get("/ai/chat-history") });

  const ask = useMutation({
    mutationFn: (q: string) => api.post("/ai/ask", { question: q }),
    onMutate: () => setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chat-history"] });
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100);
    },
  });

  const send = (q?: string) => {
    const text = (q ?? input).trim();
    if (!text || ask.isPending) return;
    setInput("");
    ask.mutate(text);
  };

  const messages = history || [];
  const empty = messages.length === 0 && !ask.isPending;

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Ask Fmail" subtitle="Your communication chief of staff" showSearch={false} showMenu />
      <KeyboardAvoidingView behavior="padding" style={{ flex: 1 }} keyboardVerticalOffset={0}>
        <ScrollView ref={scrollRef} contentContainerStyle={{ padding: spacing.lg, paddingBottom: 16, flexGrow: 1 }}>
          {empty ? (
            <View style={{ flex: 1, justifyContent: "center", paddingVertical: 20 }}>
              <View style={{ alignItems: "center", marginBottom: 24 }}>
                <View style={{ width: 72, height: 72, borderRadius: 24, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" }}>
                  <Icon name="robot-happy-outline" size={38} color={colors.brandPrimary} />
                </View>
                <T size={20} weight="800" style={{ marginTop: 14 }}>How can I help?</T>
                <T size={14} color={colors.muted} style={{ marginTop: 4, textAlign: "center" }}>I understand your emails, meetings, tasks, calendar and memory.</T>
              </View>
              <View style={{ gap: 10 }}>
                {SUGGESTIONS.map((s) => (
                  <Pressable key={s} testID={`suggestion-${s.slice(0, 8)}`} onPress={() => send(s)}
                    style={{ flexDirection: "row", alignItems: "center", gap: 10, backgroundColor: colors.surfaceSecondary, padding: 14, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border }}>
                    <Icon name="lightning-bolt-outline" size={18} color={colors.brandPrimary} />
                    <Text style={{ flex: 1, color: colors.onSurface, fontSize: 14, fontWeight: "500" }}>{s}</Text>
                  </Pressable>
                ))}
              </View>
            </View>
          ) : (
            messages.map((m: any) => (
              <View key={m.id} style={{ marginBottom: 16 }}>
                <View style={{ alignSelf: "flex-end", maxWidth: "85%", backgroundColor: colors.brandPrimary, paddingHorizontal: 16, paddingVertical: 11, borderRadius: 20, borderBottomRightRadius: 6 }}>
                  <Text style={{ color: colors.onBrandPrimary, fontSize: 15 }}>{m.q}</Text>
                </View>
                <View style={{ alignSelf: "flex-start", maxWidth: "90%", backgroundColor: colors.surfaceSecondary, paddingHorizontal: 16, paddingVertical: 12, borderRadius: 20, borderBottomLeftRadius: 6, marginTop: 8, borderWidth: 1, borderColor: colors.border }}>
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 4 }}>
                    <Icon name="brain" size={14} color={colors.brandPrimary} />
                    <Text style={{ color: colors.brandPrimary, fontSize: 11, fontWeight: "800" }}>FMAIL AI</Text>
                  </View>
                  <Text style={{ color: colors.onSurface, fontSize: 15, lineHeight: 22 }}>{m.a}</Text>
                </View>
              </View>
            ))
          )}
          {ask.isPending ? (
            <View style={{ alignSelf: "flex-start", flexDirection: "row", gap: 8, alignItems: "center", backgroundColor: colors.surfaceSecondary, padding: 14, borderRadius: 20, borderWidth: 1, borderColor: colors.border }}>
              <ActivityIndicator color={colors.brandPrimary} size="small" />
              <Text style={{ color: colors.muted }}>Thinking…</Text>
            </View>
          ) : null}
        </ScrollView>

        <KeyboardStickyView>
          <View style={{ flexDirection: "row", gap: 8, padding: spacing.md, paddingBottom: insets.bottom > 0 ? insets.bottom : spacing.md, backgroundColor: colors.surfaceSecondary, borderTopWidth: 1, borderTopColor: colors.border, alignItems: "flex-end" }}>
            <View style={{ flex: 1 }}>
              <Field placeholder="Ask about your communication…" value={input} onChangeText={setInput} testID="ask-input" multiline />
            </View>
            <Pressable testID="ask-send" onPress={() => send()} disabled={!input.trim() || ask.isPending}
              style={{ width: 48, height: 48, borderRadius: 16, backgroundColor: input.trim() ? colors.brandPrimary : colors.surfaceTertiary, alignItems: "center", justifyContent: "center" }}>
              <Icon name="arrow-up" size={24} color={input.trim() ? "#fff" : colors.muted} />
            </Pressable>
          </View>
        </KeyboardStickyView>
      </KeyboardAvoidingView>
    </View>
  );
}
