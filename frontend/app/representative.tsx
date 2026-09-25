import React, { useState, useEffect } from "react";
import { View, Text, ScrollView, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Button, Loading, Field } from "@/src/ui";
import { Header } from "@/src/screen";

const MODES = ["AI Representative", "AI Presenter", "AI Sales Representative", "AI Customer Support Representative", "AI Interview Assistant", "AI Meeting Delegate", "AI Product Demo Agent", "AI Research Representative", "AI Founder Assistant"];
const PERMS: { key: string; label: string; sensitive?: boolean }[] = [
  { key: "read", label: "Read authorized context" },
  { key: "speak", label: "Speak in meeting" },
  { key: "present", label: "Present documents" },
  { key: "files", label: "Access files" },
  { key: "negotiate", label: "Negotiate", sensitive: true },
  { key: "decisions", label: "Make decisions", sensitive: true },
  { key: "sending", label: "Send on your behalf", sensitive: true },
  { key: "financial", label: "Financial actions", sensitive: true },
];

export default function Representative() {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["representative"], queryFn: () => api.get("/representative") });
  const [rep, setRep] = useState<any>(null);
  useEffect(() => { if (data) setRep(data); }, [data]);

  const save = useMutation({ mutationFn: (b: any) => api.put("/representative", b), onSuccess: () => qc.invalidateQueries({ queryKey: ["representative"] }) });

  if (isLoading || !rep) return <View style={{ flex: 1, backgroundColor: colors.surface }}><Header title="AI Representative" back showSearch={false} /><Loading /></View>;

  const setPerm = (k: string, v: boolean) => setRep({ ...rep, perms: { ...rep.perms, [k]: v } });

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="AI Representative" subtitle="Attends meetings on your behalf" back showSearch={false} />
      <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 100 }}>
        <Card style={{ backgroundColor: colors.brandTertiary, borderColor: colors.brandPrimary + "33", marginBottom: 16, flexDirection: "row", gap: 10 }}>
          <Icon name="shield-account-outline" size={22} color={colors.brandPrimary} />
          <T size={13} color={colors.onBrandTertiary} style={{ flex: 1 }}>Your AI always identifies itself as an AI and never claims to be you. High-impact actions require your approval.</T>
        </Card>

        <T size={13} weight="800" color={colors.muted} style={{ marginBottom: 8 }}>MODE</T>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 18 }}>
          {MODES.map((m) => (
            <Pressable key={m} testID={`rep-mode-${m.split(" ")[1]?.toLowerCase()}`} onPress={() => setRep({ ...rep, mode: m })} style={{ paddingHorizontal: 12, paddingVertical: 9, borderRadius: radius.pill, backgroundColor: rep.mode === m ? colors.brandPrimary : colors.surfaceTertiary }}>
              <Text style={{ color: rep.mode === m ? "#fff" : colors.onSurfaceTertiary, fontWeight: "600", fontSize: 12 }}>{m}</Text>
            </Pressable>
          ))}
        </View>

        <T size={13} weight="800" color={colors.muted} style={{ marginBottom: 8 }}>INSTRUCTIONS</T>
        <Field placeholder="e.g. Explain our product and pricing. Do not approve discounts below ₹50,000. Ask me for anything outside your authority." value={rep.instructions} onChangeText={(t: string) => setRep({ ...rep, instructions: t })} multiline testID="rep-instructions" />

        <T size={13} weight="800" color={colors.muted} style={{ marginTop: 18, marginBottom: 8 }}>NEGOTIATION FLOOR (₹)</T>
        <Field placeholder="50000" value={String(rep.negotiationFloor)} onChangeText={(t: string) => setRep({ ...rep, negotiationFloor: parseInt(t.replace(/\D/g, "")) || 0 })} keyboardType="number-pad" testID="rep-floor" />

        <T size={13} weight="800" color={colors.muted} style={{ marginTop: 18, marginBottom: 8 }}>PERMISSIONS</T>
        <Card style={{ paddingVertical: 4 }}>
          {PERMS.map((p, i) => (
            <View key={p.key} style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 12, borderBottomWidth: i === PERMS.length - 1 ? 0 : 1, borderBottomColor: colors.divider }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                <T size={14}>{p.label}</T>
                {p.sensitive ? <View style={{ backgroundColor: colors.error + "22", paddingHorizontal: 7, paddingVertical: 2, borderRadius: 6 }}><Text style={{ color: colors.error, fontSize: 10, fontWeight: "800" }}>SENSITIVE</Text></View> : null}
              </View>
              <Pressable testID={`perm-${p.key}`} onPress={() => setPerm(p.key, !rep.perms[p.key])}><Icon name={rep.perms[p.key] ? "toggle-switch" : "toggle-switch-off-outline"} size={36} color={rep.perms[p.key] ? colors.brandPrimary : colors.muted} /></Pressable>
            </View>
          ))}
        </Card>

        <Card style={{ marginTop: 16 }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <Icon name="account-arrow-right-outline" size={18} color={colors.brandPrimary} />
            <T size={13} weight="800" color={colors.muted}>HUMAN HANDOFF PREVIEW</T>
          </View>
          <T size={14} style={{ lineHeight: 21 }}>{`"Client is requesting ₹${Math.max(0, (rep.negotiationFloor || 0) - 10000).toLocaleString()}. Your configured minimum is ₹${(rep.negotiationFloor || 0).toLocaleString()}. Would you like to join?"`}</T>
        </Card>
      </ScrollView>
      <View style={{ position: "absolute", left: 0, right: 0, bottom: 0, padding: spacing.md, paddingBottom: insets.bottom + 8, backgroundColor: colors.surfaceSecondary, borderTopWidth: 1, borderTopColor: colors.border }}>
        <Button title="Save configuration" icon="content-save-outline" testID="rep-save" loading={save.isPending} onPress={() => save.mutate(rep)} />
      </View>
    </View>
  );
}
