import React from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTheme, spacing } from "@/src/theme";
import { Header } from "@/src/screen";
import { T } from "@/src/ui";

export default function Terms() {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  return <View style={[styles.page, { backgroundColor: colors.surface }]}><Header title="Terms & Conditions" back showSearch={false} /><ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 32 }}><T color={colors.muted} size={12}>Last updated: 29 September 2026</T><Text style={[styles.heading, { color: colors.onSurface }]}>Using Fmail</Text><T style={styles.body}>Fmail is a communication and productivity service. You are responsible for the accounts you connect, the content you send, and keeping your sign-in details secure.</T><Text style={[styles.heading, { color: colors.onSurface }]}>Connected services</Text><T style={styles.body}>When you connect Gmail or another service, you authorize Fmail to access only the scopes you approve. You can revoke access in your provider settings at any time. Fmail may stop syncing when access is revoked, expired, or unavailable.</T><Text style={[styles.heading, { color: colors.onSurface }]}>Acceptable use</Text><T style={styles.body}>Do not use Fmail for unlawful activity, abuse, unsolicited bulk messaging, impersonation, credential misuse, or content that harms others. You must comply with the terms of every connected provider.</T><Text style={[styles.heading, { color: colors.onSurface }]}>Availability and support</Text><T style={styles.body}>Features may depend on third-party providers, network availability, and device permissions. For support, contact jarvisai9077@gmail.com.</T><Text style={[styles.heading, { color: colors.onSurface }]}>Changes</Text><T style={styles.body}>We may update these terms as the service changes. Continued use after an update means you accept the revised terms.</T></ScrollView></View>;
}
const styles = StyleSheet.create({ page: { flex: 1 }, heading: { fontSize: 18, fontWeight: "800", marginTop: 24, marginBottom: 8 }, body: { lineHeight: 23 }});
