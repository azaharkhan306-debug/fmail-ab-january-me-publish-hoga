import React, { useState } from "react";
import { View, Text, ScrollView, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useAuth } from "@/src/auth";
import { setColorScheme, useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Button, Avatar, Badge, Sheet, Field } from "@/src/ui";
import { Header } from "@/src/screen";

const ACC_ICON: Record<string, string> = { fmail: "at", gmail: "google", outlook: "microsoft-outlook", yahoo: "yahoo" };

export default function Settings() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { user, logout, setUser } = useAuth();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [name, setName] = useState(user?.name || "");
  const [sig, setSig] = useState(user?.signature || "");

  const update = async (b: any) => {
    const u = await api.put("/auth/profile", b);
    setUser(u);
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Settings" back showSearch={false} />
      <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 20 }}>
        <Card style={{ alignItems: "center", marginBottom: 16 }}>
          <Avatar name={user?.name || "U"} size={72} uri={user?.photo} />
          <T size={20} weight="800" style={{ marginTop: 12 }}>{user?.name}</T>
          <View style={{ backgroundColor: colors.brandTertiary, paddingHorizontal: 12, paddingVertical: 5, borderRadius: radius.pill, marginTop: 6 }}>
            <Text style={{ color: colors.onBrandTertiary, fontWeight: "700" }}>{user?.fmail}</Text>
          </View>
          <Button title="Edit profile" variant="secondary" small icon="pencil-outline" testID="edit-profile" onPress={() => setEditOpen(true)} style={{ marginTop: 14 }} />
        </Card>

        <SectionTitle text="CONNECTED ACCOUNTS" />
        <Card style={{ marginBottom: 16, paddingVertical: 4 }}>
          {(user?.connectedAccounts || []).map((a: any, i: number) => (
            <View key={i} style={{ flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 12, borderBottomWidth: i === (user?.connectedAccounts?.length || 0) - 1 ? 0 : 1, borderBottomColor: colors.divider }}>
              <Icon name={ACC_ICON[a.provider] || "email"} size={22} color={colors.onSurface} />
              <View style={{ flex: 1 }}>
                <T size={14} weight="700" style={{ textTransform: "capitalize" }}>{a.provider}</T>
                <T size={12} color={colors.muted}>{a.email || "Not connected"}</T>
              </View>
              <Badge label={a.connected ? "Connected" : "Connect"} color={a.connected ? colors.success : colors.muted} tone="soft" />
            </View>
          ))}
        </Card>

        <SectionTitle text="AI & PRIVACY" />
        <Card style={{ marginBottom: 16, paddingVertical: 4 }}>
          <Toggle label="AI features" desc="Classification, summaries, replies" value={user?.aiEnabled !== false} onToggle={(v) => update({ aiEnabled: v })} testID="toggle-ai" />
          <Toggle label="Fmail Memory" desc="Remember people, projects, decisions" value={user?.memoryEnabled !== false} onToggle={(v) => update({ memoryEnabled: v })} testID="toggle-memory" last />
        </Card>

        <SectionTitle text="APPEARANCE" />
        <Card style={{ marginBottom: 16 }}>
          <View style={{ flexDirection: "row", gap: 8 }}>
            {[{ k: "light", i: "white-balance-sunny" }, { k: "dark", i: "weather-night" }, { k: "system", i: "cellphone" }].map((m) => (
              <Pressable key={m.k} testID={`theme-${m.k}`} onPress={() => { setColorScheme(m.k === "system" ? null : (m.k as any)); update({ darkMode: m.k }); }}
                style={{ flex: 1, alignItems: "center", gap: 6, paddingVertical: 14, borderRadius: radius.md, backgroundColor: user?.darkMode === m.k ? colors.brandPrimary : colors.surfaceTertiary }}>
                <Icon name={m.i} size={22} color={user?.darkMode === m.k ? "#fff" : colors.onSurface} />
                <Text style={{ color: user?.darkMode === m.k ? "#fff" : colors.onSurfaceTertiary, fontWeight: "600", textTransform: "capitalize", fontSize: 13 }}>{m.k}</Text>
              </Pressable>
            ))}
          </View>
        </Card>

        <SectionTitle text="INTELLIGENCE" />
        <Card style={{ marginBottom: 16, paddingVertical: 4 }}>
          <Row icon="account-arrow-right-outline" label="Follow-up Brain" onPress={() => router.push("/followups")} testID="nav-followups" />
          <Row icon="shield-account-outline" label="AI Representative" onPress={() => router.push("/representative")} testID="nav-rep" />
          <Row icon="history" label="AI Activity & Audit Log" onPress={() => router.push("/audit")} testID="nav-audit" last />
        </Card>

        <SectionTitle text="DATA & SECURITY" />
        <Card style={{ marginBottom: 16, paddingVertical: 4 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 12 }}>
            <Icon name="firework" size={20} color={colors.brandPrimary} />
            <T size={14} style={{ flex: 1 }}>Firebase</T>
            <Badge label="Connected" color={colors.success} tone="soft" />
          </View>
          <Row icon="download-outline" label="Export my data" onPress={() => {}} testID="export-data" />
          <Row icon="lock-outline" label="Encryption in transit" onPress={() => {}} value="TLS" last />
        </Card>

        <Button title="Sign out" variant="danger" icon="logout" testID="logout" onPress={async () => { await logout(); router.replace("/(auth)/welcome"); }} />
        <T size={12} color={colors.muted} style={{ textAlign: "center", marginTop: 16 }}>Fmail · Your Communication OS</T>
      </ScrollView>

      <Sheet visible={editOpen} onClose={() => setEditOpen(false)} title="Edit profile" testID="edit-sheet">
        <T size={13} weight="700" color={colors.muted} style={{ marginBottom: 6 }}>DISPLAY NAME</T>
        <Field placeholder="Your name" value={name} onChangeText={setName} testID="edit-name" />
        <T size={13} weight="700" color={colors.muted} style={{ marginTop: 14, marginBottom: 6 }}>SIGNATURE</T>
        <Field placeholder="Email signature" value={sig} onChangeText={setSig} multiline testID="edit-signature" />
        <Button title="Save" icon="content-save-outline" testID="edit-save" onPress={() => { update({ name, signature: sig }); setEditOpen(false); }} style={{ marginTop: 18 }} />
      </Sheet>
    </View>
  );
}

function SectionTitle({ text }: { text: string }) {
  const { colors } = useTheme();
  return <Text style={{ color: colors.muted, fontWeight: "800", fontSize: 12, marginBottom: 8, letterSpacing: 0.5 }}>{text}</Text>;
}
function Toggle({ label, desc, value, onToggle, last, testID }: any) {
  const { colors } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", paddingVertical: 12, borderBottomWidth: last ? 0 : 1, borderBottomColor: colors.divider }}>
      <View style={{ flex: 1 }}><T size={14} weight="600">{label}</T><T size={12} color={colors.muted}>{desc}</T></View>
      <Pressable testID={testID} onPress={() => onToggle(!value)}><Icon name={value ? "toggle-switch" : "toggle-switch-off-outline"} size={36} color={value ? colors.brandPrimary : colors.muted} /></Pressable>
    </View>
  );
}
function Row({ icon, label, onPress, value, last, testID }: any) {
  const { colors } = useTheme();
  return (
    <Pressable testID={testID} onPress={onPress} style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 13, borderBottomWidth: last ? 0 : 1, borderBottomColor: colors.divider }}>
      <Icon name={icon} size={20} color={colors.onSurface} />
      <T size={14} style={{ flex: 1 }}>{label}</T>
      {value ? <T size={13} color={colors.muted}>{value}</T> : <Icon name="chevron-right" size={22} color={colors.muted} />}
    </Pressable>
  );
}
