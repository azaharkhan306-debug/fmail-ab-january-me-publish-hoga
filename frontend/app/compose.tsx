import React, { useState } from "react";
import { View, Text, Pressable } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter, useLocalSearchParams } from "expo-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { useTheme, spacing } from "@/src/theme";
import { Icon, T, Button, Field } from "@/src/ui";
import { Header } from "@/src/screen";

export default function Compose() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user } = useAuth();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const params = useLocalSearchParams<{ to?: string }>();
  const [to, setTo] = useState(params.to || "");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [err, setErr] = useState("");

  const send = useMutation({
    mutationFn: (draft: boolean) => api.post("/emails/compose", { to, subject, body: body + (user?.signature ? "\n\n" + user.signature : ""), draft }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["emails"] }); router.back(); },
  });

  const onSend = () => {
    if (!to.trim() || !subject.trim()) return setErr("Please add a recipient and subject.");
    send.mutate(false);
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Compose" back showSearch={false}
        right={<Pressable onPress={() => send.mutate(true)} testID="save-draft"><T color={colors.brandPrimary} weight="700">Save draft</T></Pressable>} />
      <KeyboardAwareScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 20 }} bottomOffset={20}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.divider }}>
          <Icon name="at" size={18} color={colors.brandPrimary} />
          <T size={13} color={colors.muted}>From</T>
          <T size={14} weight="600">{user?.fmail}</T>
        </View>
        <View style={{ gap: 12, marginTop: 14 }}>
          <Field icon="account-outline" placeholder="To" value={to} onChangeText={setTo} autoCapitalize="none" keyboardType="email-address" testID="compose-to" />
          <Field icon="format-title" placeholder="Subject" value={subject} onChangeText={setSubject} testID="compose-subject" />
          <Field placeholder="Write your message…" value={body} onChangeText={setBody} multiline testID="compose-body" style={{ minHeight: 200 }} />
        </View>
        {err ? <Text style={{ color: colors.error, marginTop: 12 }}>{err}</Text> : null}
        <Button title="Send email" icon="send" testID="compose-send" loading={send.isPending} onPress={onSend} style={{ marginTop: 20 }} />
      </KeyboardAwareScrollView>
    </View>
  );
}
