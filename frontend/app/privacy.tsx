import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTheme, spacing } from "@/src/theme";
import { Header } from "@/src/screen";
import { T } from "@/src/ui";

export default function Privacy() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  return <View style={[styles.page, { backgroundColor: colors.surface }]}><Header title="Privacy Policy" back showSearch={false} /><ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 32 }}><T color={colors.muted} size={12}>Last updated: 29 September 2026</T><Text style={[styles.heading, { color: colors.onSurface }]}>Information we use</Text><T style={styles.body}>Fmail uses account details, connected-provider tokens, email metadata, files you choose to upload, meeting data, and device notification tokens to provide the features you request. We do not send email bodies or personal identifiers to analytics.</T><Text style={[styles.heading, { color: colors.onSurface }]}>How information is protected</Text><T style={styles.body}>Provider refresh tokens are stored server-side and encrypted with the configured application key. API traffic uses HTTPS in production. Notification payloads contain only the minimum sender and subject information needed to notify you.</T><Text style={[styles.heading, { color: colors.onSurface }]}>Third-party services</Text><T style={styles.body}>Gmail, Firebase, Sarvam, Resend, and AI providers process data only as required for the feature you enable and under their own terms. You can disconnect providers and delete your Fmail account from Settings.</T><Text style={[styles.heading, { color: colors.onSurface }]}>Retention and deletion</Text><T style={styles.body}>Fmail retains account data while your account is active. Deleting your account removes Fmail records and push registrations. Provider-side data remains subject to that provider's policies.</T><Text style={[styles.heading, { color: colors.onSurface }]}>Contact</Text><T style={styles.body}>Privacy questions or requests can be sent to jarvisai9077@gmail.com.</T></ScrollView></View>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, heading: { fontSize: 18, fontWeight: "800", marginTop: 24, marginBottom: 8 }, body: { lineHeight: 23 }});
