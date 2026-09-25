import React, { useState } from "react";
import { View, Text, FlatList, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Button, Loading, ErrorState, Empty, Chip, Sheet, Field } from "@/src/ui";
import { Header, ChipRow } from "@/src/screen";

const KINDS = ["All", "Person", "Organization", "Project", "Decision", "Commitment"];
const KIND_ICON: Record<string, string> = { Person: "account-outline", Organization: "office-building-outline", Project: "rocket-launch-outline", Decision: "gavel", Commitment: "handshake-outline" };

export default function Memory() {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const [kind, setKind] = useState("All");
  const [open, setOpen] = useState(false);
  const [nk, setNk] = useState("Person"); const [title, setTitle] = useState(""); const [detail, setDetail] = useState("");

  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["memory"], queryFn: () => api.get("/memory") });
  const save = useMutation({ mutationFn: (b: any) => api.post("/memory", b), onSuccess: () => { qc.invalidateQueries({ queryKey: ["memory"] }); setOpen(false); setTitle(""); setDetail(""); } });
  const del = useMutation({ mutationFn: (mid: string) => api.del(`/memory/${mid}`), onSuccess: () => qc.invalidateQueries({ queryKey: ["memory"] }) });

  const list = (data || []).filter((m: any) => kind === "All" || m.kind === kind);

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Memory" subtitle="Your communication brain" back showSearch={false} />
      <ChipRow>{KINDS.map((k) => <Chip key={k} label={k} active={kind === k} onPress={() => setKind(k)} testID={`mem-${k.toLowerCase()}`} />)}</ChipRow>
      {isLoading ? <Loading /> : isError ? <ErrorState onRetry={refetch} /> : (
        <FlatList
          data={list}
          keyExtractor={(i) => i.id}
          contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 80, flexGrow: 1 }}
          ListEmptyComponent={<Empty icon="brain" title="No memories yet" subtitle="Fmail remembers people, projects and decisions." />}
          renderItem={({ item }) => (
            <Card style={{ marginBottom: 10, flexDirection: "row", gap: 12 }}>
              <View style={{ width: 42, height: 42, borderRadius: 12, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" }}>
                <Icon name={KIND_ICON[item.kind] || "brain"} size={22} color={colors.brandPrimary} />
              </View>
              <View style={{ flex: 1 }}>
                <T size={15} weight="700">{item.title}</T>
                <T size={11} weight="700" color={colors.brandPrimary}>{item.kind.toUpperCase()}</T>
                <T size={13} color={colors.onSurfaceTertiary} style={{ marginTop: 4 }}>{item.detail}</T>
              </View>
              <Pressable testID={`mem-del-${item.id}`} onPress={() => del.mutate(item.id)}><Icon name="close" size={20} color={colors.muted} /></Pressable>
            </Card>
          )}
        />
      )}
      <Pressable testID="mem-fab" onPress={() => setOpen(true)} style={{ position: "absolute", right: 20, bottom: insets.bottom + 16, width: 58, height: 58, borderRadius: 20, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", elevation: 6 }}>
        <Icon name="plus" size={28} color="#fff" />
      </Pressable>
      <Sheet visible={open} onClose={() => setOpen(false)} title="New memory" testID="mem-sheet">
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
          {KINDS.slice(1).map((k) => <Pressable key={k} onPress={() => setNk(k)} style={{ paddingHorizontal: 12, height: 34, borderRadius: radius.pill, justifyContent: "center", backgroundColor: nk === k ? colors.brandPrimary : colors.surfaceTertiary }}><Text style={{ color: nk === k ? "#fff" : colors.onSurfaceTertiary, fontWeight: "600", fontSize: 13 }}>{k}</Text></Pressable>)}
        </View>
        <Field placeholder="Title (e.g. Rahul Verma)" value={title} onChangeText={setTitle} testID="mem-title" />
        <View style={{ marginTop: 12 }}><Field placeholder="What should Fmail remember?" value={detail} onChangeText={setDetail} multiline testID="mem-detail" /></View>
        <Button title="Save memory" icon="content-save-outline" testID="mem-save" onPress={() => { if (title.trim()) save.mutate({ kind: nk, title, detail }); }} style={{ marginTop: 20 }} />
      </Sheet>
    </View>
  );
}
