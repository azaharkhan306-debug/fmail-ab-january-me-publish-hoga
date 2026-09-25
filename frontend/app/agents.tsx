import React, { useState } from "react";
import { View, Text, ScrollView, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Button, Loading, ErrorState, Chip, Badge, Sheet, Field } from "@/src/ui";
import { Header, ChipRow } from "@/src/screen";

const CATS = ["All", "Fmail Agents", "Trending", "Students", "Business", "Productivity", "Finance", "Travel", "Shopping", "Developers", "Enterprise"];

export default function Agents() {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"store" | "installed">("store");
  const [cat, setCat] = useState("All");
  const [sel, setSel] = useState<any>(null);
  const [build, setBuild] = useState(false);
  const [bn, setBn] = useState(""); const [bd, setBd] = useState(""); const [bi, setBi] = useState("");

  const market = useQuery({ queryKey: ["marketplace"], queryFn: () => api.get("/agents/marketplace") });
  const installed = useQuery({ queryKey: ["installed"], queryFn: () => api.get("/agents/installed") });

  const install = useMutation({ mutationFn: (b: any) => api.post("/agents/install", b), onSuccess: () => { qc.invalidateQueries({ queryKey: ["marketplace"] }); qc.invalidateQueries({ queryKey: ["installed"] }); setSel(null); setBuild(false); setBn(""); setBd(""); setBi(""); } });
  const toggle = useMutation({ mutationFn: (aid: string) => api.post(`/agents/${aid}/toggle`), onSuccess: () => qc.invalidateQueries({ queryKey: ["installed"] }) });
  const uninstall = useMutation({ mutationFn: (aid: string) => api.del(`/agents/${aid}`), onSuccess: () => { qc.invalidateQueries({ queryKey: ["installed"] }); qc.invalidateQueries({ queryKey: ["marketplace"] }); } });

  const marketList = (market.data || []).filter((a: any) => cat === "All" || cat === "Fmail Agents" || cat === "Trending" ? true : a.cat === cat);

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="AI Agents" subtitle="An app store for AI agents" back showSearch={false}
        right={<Pressable onPress={() => setBuild(true)} testID="agent-build"><Icon name="hammer-wrench" size={24} color={colors.brandPrimary} /></Pressable>} />

      <View style={{ flexDirection: "row", paddingHorizontal: spacing.lg, gap: 8 }}>
        {(["store", "installed"] as const).map((t) => (
          <Pressable key={t} testID={`agent-tab-${t}`} onPress={() => setTab(t)} style={{ flex: 1, paddingVertical: 10, borderRadius: radius.md, backgroundColor: tab === t ? colors.brandPrimary : colors.surfaceSecondary, alignItems: "center", borderWidth: 1, borderColor: tab === t ? colors.brandPrimary : colors.border }}>
            <Text style={{ color: tab === t ? "#fff" : colors.onSurface, fontWeight: "700" }}>{t === "store" ? "Marketplace" : "Installed"}</Text>
          </Pressable>
        ))}
      </View>

      {tab === "store" ? (
        <>
          <ChipRow>{CATS.map((c) => <Chip key={c} label={c} active={cat === c} onPress={() => setCat(c)} testID={`agentcat-${c.split(" ")[0].toLowerCase()}`} />)}</ChipRow>
          {market.isLoading ? <Loading /> : market.isError ? <ErrorState onRetry={market.refetch} /> : (
            <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 20 }}>
              {marketList.map((a: any) => (
                <Card key={a.name} testID={`agent-${a.name.replace(/\s/g, "-")}`} onPress={() => setSel(a)} style={{ marginBottom: 10 }}>
                  <View style={{ flexDirection: "row", gap: 12, alignItems: "center" }}>
                    <View style={{ width: 46, height: 46, borderRadius: 13, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" }}>
                      <Icon name="robot-outline" size={24} color={colors.brandPrimary} />
                    </View>
                    <View style={{ flex: 1 }}>
                      <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                        <T size={15} weight="700">{a.name}</T>
                        {a.verified ? <Icon name="check-decagram" size={15} color={colors.info} /> : null}
                      </View>
                      <T size={12} color={colors.muted} numberOfLines={1}>{a.desc}</T>
                      <View style={{ flexDirection: "row", gap: 10, marginTop: 4 }}>
                        <T size={11} color={colors.muted}>★ {a.rating}</T>
                        <T size={11} color={colors.muted}>{a.installs} installs</T>
                      </View>
                    </View>
                    {a.installed ? <Badge label="Installed" color={colors.success} tone="soft" /> :
                      <Button title="Get" small onPress={() => install.mutate({ name: a.name })} testID={`install-${a.name.replace(/\s/g, "-")}`} />}
                  </View>
                </Card>
              ))}
            </ScrollView>
          )}
        </>
      ) : (
        installed.isLoading ? <Loading /> : (
          <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 20 }}>
            {(installed.data || []).map((a: any) => (
              <Card key={a.id} style={{ marginBottom: 10, flexDirection: "row", gap: 12, alignItems: "center" }}>
                <View style={{ width: 42, height: 42, borderRadius: 12, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" }}>
                  <Icon name="robot-outline" size={22} color={colors.brandPrimary} />
                </View>
                <View style={{ flex: 1 }}>
                  <T size={15} weight="700">{a.name}</T>
                  <T size={12} color={colors.muted} numberOfLines={1}>{a.desc || "Custom agent"}</T>
                </View>
                <Pressable testID={`toggle-${a.id}`} onPress={() => toggle.mutate(a.id)}><Icon name={a.enabled ? "toggle-switch" : "toggle-switch-off-outline"} size={36} color={a.enabled ? colors.brandPrimary : colors.muted} /></Pressable>
                <Pressable testID={`uninstall-${a.id}`} onPress={() => uninstall.mutate(a.id)}><Icon name="trash-can-outline" size={20} color={colors.muted} /></Pressable>
              </Card>
            ))}
          </ScrollView>
        )
      )}

      <Sheet visible={!!sel} onClose={() => setSel(null)} title={sel?.name} testID="agent-detail-sheet">
        {sel ? (
          <>
            <T size={15} color={colors.onSurfaceTertiary} style={{ lineHeight: 22, marginBottom: 16 }}>{sel.desc}</T>
            <T size={13} weight="800" color={colors.muted} style={{ marginBottom: 8 }}>REQUIRED PERMISSIONS</T>
            {(sel.perms || []).map((p: string) => (
              <View key={p} style={{ flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 6 }}>
                <Icon name="shield-check-outline" size={18} color={colors.success} />
                <T size={14}>{p}</T>
              </View>
            ))}
            <T size={12} color={colors.muted} style={{ marginTop: 10 }}>Sensitive actions like sending or financial actions always require your explicit approval.</T>
            {sel.installed ? <Badge label="Installed" color={colors.success} tone="soft" /> :
              <Button title={`Install ${sel.name}`} icon="download" testID="install-detail" loading={install.isPending} onPress={() => install.mutate({ name: sel.name })} style={{ marginTop: 16 }} />}
          </>
        ) : null}
      </Sheet>

      <Sheet visible={build} onClose={() => setBuild(false)} title="Agent Builder" testID="builder-sheet">
        <View style={{ gap: 12 }}>
          <Field icon="robot-outline" placeholder="Agent name" value={bn} onChangeText={setBn} testID="builder-name" />
          <Field placeholder="Description" value={bd} onChangeText={setBd} testID="builder-desc" />
          <Field placeholder="Instructions — what should it do?" value={bi} onChangeText={setBi} multiline testID="builder-instructions" />
        </View>
        <T size={12} color={colors.muted} style={{ marginTop: 12 }}>Your agent runs with scoped permissions and can be disabled anytime.</T>
        <Button title="Create & install agent" icon="rocket-launch-outline" testID="builder-create" loading={install.isPending} onPress={() => { if (bn.trim()) install.mutate({ name: bn, desc: bd, instructions: bi }); }} style={{ marginTop: 16 }} />
      </Sheet>
    </View>
  );
}
