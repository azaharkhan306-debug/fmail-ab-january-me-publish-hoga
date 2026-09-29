import React, { useState } from "react";
import { Keyboard, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { api } from "@/src/api";
import { track } from "@/src/analytics";
import { useTheme, spacing } from "@/src/theme";
import { Header } from "@/src/screen";
import { Button, Field, T } from "@/src/ui";

export default function Feedback() {
  const { colors } = useTheme(); const insets = useSafeAreaInsets(); const router = useRouter();
  const [message, setMessage] = useState(""); const [category, setCategory] = useState("general"); const [error, setError] = useState(""); const [sent, setSent] = useState(false); const [busy, setBusy] = useState(false);
  const submit = async () => { Keyboard.dismiss(); setError(""); if (message.trim().length < 5) return setError("Please share at least a few words."); setBusy(true); try { await api.post("/feedback", { message: message.trim(), category }); await track("feedback_sent", { category }); setSent(true); } catch (e: any) { setError(e?.message || "Could not send feedback. Please try again."); } finally { setBusy(false); } };
  return <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} style={[styles.page, { backgroundColor: colors.surface }]}><Header title="Send feedback" back showSearch={false} /><Pressable style={styles.flex} onPress={Keyboard.dismiss}><View style={{ padding: spacing.lg, paddingBottom: insets.bottom + 24 }}>{sent ? <><T size={20} weight="800">Thanks for helping improve Fmail.</T><T color={colors.muted} style={{ marginTop: 8 }}>Your feedback was sent to our support team.</T><Button title="Done" onPress={() => router.back()} style={{ marginTop: 24 }} /></> : <><T size={15} color={colors.muted} style={{ marginBottom: 16 }}>Tell us what worked, what failed, or what you would like to improve.</T><Field placeholder="Your feedback" value={message} onChangeText={setMessage} multiline testID="feedback-message" style={{ minHeight: 160 }} /><Field placeholder="Category (general, bug, idea)" value={category} onChangeText={setCategory} testID="feedback-category" style={{ marginTop: 12 }} />{error ? <Text style={{ color: colors.error, marginTop: 10 }}>{error}</Text> : null}<Button title="Send feedback" onPress={submit} loading={busy} testID="feedback-submit" style={{ marginTop: 18 }} /></>}</View></Pressable></KeyboardAvoidingView>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, flex: { flex: 1 }});
