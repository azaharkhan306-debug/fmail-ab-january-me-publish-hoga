import React, { useEffect, useState } from "react";
import { Alert, Linking, Platform, Share, StyleSheet, View } from "react-native";
import * as WebBrowser from "expo-web-browser";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { api } from "@/src/api";
import { track } from "@/src/analytics";
import { useTheme, spacing } from "@/src/theme";
import { Header } from "@/src/screen";
import { Button, Card, T } from "@/src/ui";

export default function Gmail() {
  const { colors } = useTheme(); const insets = useSafeAreaInsets(); const router = useRouter(); const [configured, setConfigured] = useState<boolean | null>(null); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  useEffect(() => { api.get("/auth/google/config").then((r) => setConfigured(!!r.configured)).catch((e) => setError(e.message)); }, []);
  const connect = async () => { setError(""); setBusy(true); try { const r = await api.get("/auth/google/authorize"); const redirect = `${process.env.EXPO_PUBLIC_BACKEND_URL}/api/auth/google/callback`; const result = await WebBrowser.openAuthSessionAsync(r.url, redirect); if (result.type === "success") { await api.post("/gmail/sync"); await track("gmail_connected"); Alert.alert("Gmail connected", "Your inbox will sync automatically."); router.back(); } } catch (e: any) { setError(e?.message || "Could not connect Gmail."); } finally { setBusy(false); } };
  return <View style={[styles.page, { backgroundColor: colors.surface }]}><Header title="Connect Gmail" back showSearch={false} /><View style={{ padding: spacing.lg, paddingBottom: insets.bottom + 24 }}><Card><T size={19} weight="800">Gmail and Google Workspace</T><T color={colors.muted} style={{ marginTop: 8, lineHeight: 21 }}>Fmail uses Gmail API OAuth. You choose the permissions, can revoke access any time, and new inbox messages are synchronized without filtering by sender.</T><Button title="Connect with Google" icon="google" disabled={configured === false || configured === null} loading={busy} onPress={connect} style={{ marginTop: 20 }} />{configured === false ? <T color={colors.error} size={12} style={{ marginTop: 10 }}>Google OAuth is not configured for the Fmail project yet.</T> : null}{error ? <T color={colors.error} size={13} style={{ marginTop: 10 }}>{error}</T> : null}</Card></View></View>;
}
const styles = StyleSheet.create({ page: { flex: 1 }});
