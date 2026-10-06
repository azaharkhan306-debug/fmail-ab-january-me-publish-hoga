import React, { useEffect, useState } from "react";
import { Alert, StyleSheet, View } from "react-native";
import * as WebBrowser from "expo-web-browser";
import * as Linking from "expo-linking";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { api } from "@/src/api";
import { track } from "@/src/analytics";
import { useAuth } from "@/src/auth";
import { useTheme, spacing } from "@/src/theme";
import { Header } from "@/src/screen";
import { Button, Card, T } from "@/src/ui";

export default function Gmail() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user, refresh } = useAuth();
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [status, setStatus] = useState<{ connected: boolean; email?: string; needsReconnect?: boolean } | null>(null);
  const [busy, setBusy] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");

  const loadStatus = async () => {
    try {
      const cfg = await api.get("/auth/google/config");
      setConfigured(!!cfg.configured);
      const st = await api.get("/gmail/status");
      setStatus(st);
    } catch (e: any) {
      setError(e?.message || "Could not load Gmail status.");
    }
  };

  useEffect(() => { loadStatus(); }, []);

  const connect = async () => {
    setError(""); setBusy(true);
    try {
      const r = await api.get("/auth/google/authorize");
      const returnUrl = Linking.createURL("gmail");
      const result = await WebBrowser.openAuthSessionAsync(r.url, returnUrl);
      if (result.type === "success" && result.url) {
        const parsed = Linking.parse(result.url);
        if (parsed.queryParams?.error) throw new Error("Google connection was not completed. Please try again.");
      } else if (result.type === "cancel" || result.type === "dismiss") {
        setBusy(false); return;
      }
      await api.post("/gmail/sync");
      await track("gmail_connected");
      await refresh();
      await loadStatus();
      Alert.alert("Gmail connected", "Your inbox is syncing now.");
      router.back();
    } catch (e: any) {
      setError(e?.message || "Could not connect Gmail.");
    } finally {
      setBusy(false);
    }
  };

  const syncNow = async () => {
    setError(""); setSyncing(true);
    try {
      const r = await api.post("/gmail/sync");
      Alert.alert("Gmail", r?.imported ? `${r.imported} new email(s) synced.` : "Your inbox is up to date.");
    } catch (e: any) {
      setError(e?.message || "Sync failed. Please try again.");
    } finally {
      setSyncing(false);
    }
  };

  const disconnect = async () => {
    Alert.alert("Disconnect Gmail", "This removes your Gmail connection and synced mail from Fmail.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Disconnect", style: "destructive", onPress: async () => {
          try {
            await api.post("/gmail/disconnect");
            await refresh();
            await loadStatus();
          } catch (e: any) { setError(e?.message || "Could not disconnect."); }
        },
      },
    ]);
  };

  const connected = status?.connected || user?.gmailConnected;

  return (
    <View style={[styles.page, { backgroundColor: colors.surface }]}>
      <Header title="Connect Gmail" back showSearch={false} />
      <View style={{ padding: spacing.lg, paddingBottom: insets.bottom + 24, gap: 16 }}>
        <Card>
          <T size={19} weight="800">Gmail and Google Workspace</T>
          <T color={colors.muted} style={{ marginTop: 8, lineHeight: 21 }}>
            Fmail connects securely to your Gmail using Google OAuth and the Gmail API. You choose the
            permissions and can revoke access any time. Fmail never stores your Google password.
          </T>

          {connected ? (
            <>
              <View style={{ marginTop: 16, padding: 12, borderRadius: 12, backgroundColor: colors.surfaceSecondary, borderWidth: 1, borderColor: colors.border }}>
                <T size={12} color={colors.muted}>Connected account</T>
                <T size={15} weight="700" style={{ marginTop: 2 }}>{status?.email || user?.gmailEmail}</T>
              </View>
              {status?.needsReconnect ? (
                <T color={colors.error} size={13} style={{ marginTop: 10 }}>Access expired — please reconnect to keep syncing.</T>
              ) : null}
              <Button title="Sync now" icon="sync" loading={syncing} onPress={syncNow} style={{ marginTop: 16 }} />
              {status?.needsReconnect ? (
                <Button title="Reconnect Gmail" icon="google" loading={busy} onPress={connect} variant="secondary" style={{ marginTop: 10 }} />
              ) : null}
              <Button title="Disconnect" icon="link-off" variant="ghost" onPress={disconnect} style={{ marginTop: 10 }} />
            </>
          ) : (
            <>
              <Button title="Connect with Google" icon="google" disabled={configured === false || configured === null} loading={busy} onPress={connect} style={{ marginTop: 20 }} />
              {configured === false ? <T color={colors.error} size={12} style={{ marginTop: 10 }}>Google OAuth is not configured for the Fmail project yet.</T> : null}
            </>
          )}
          {error ? <T color={colors.error} size={13} style={{ marginTop: 10 }}>{error}</T> : null}
        </Card>
      </View>
    </View>
  );
}
const styles = StyleSheet.create({ page: { flex: 1 } });
