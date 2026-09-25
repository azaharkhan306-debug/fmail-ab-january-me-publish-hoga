import React, { useState } from "react";
import { View, Text, FlatList, Pressable, RefreshControl } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Button, Loading, ErrorState, Empty, Badge, Sheet, Field, Chip } from "@/src/ui";
import { Header, ChipRow } from "@/src/screen";

const PRIOS: Record<string, string> = { high: "#D64545", medium: "#C98A00", low: "#1E9E5A" };

export default function Tasks() {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const [f, setF] = useState("All");
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("medium");

  const { data, isLoading, isError, refetch, isRefetching } = useQuery({ queryKey: ["tasks"], queryFn: () => api.get("/tasks") });
  const save = useMutation({ mutationFn: (b: any) => api.post("/tasks", b), onSuccess: () => { qc.invalidateQueries({ queryKey: ["tasks"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); } });
  const del = useMutation({ mutationFn: (tid: string) => api.del(`/tasks/${tid}`), onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }) });

  const list = (data || []).filter((t: any) => f === "All" ? true : f === "Open" ? !t.done : f === "Done" ? t.done : t.priority === f.toLowerCase());

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Tasks" back showSearch={false} />
      <ChipRow>
        {["All", "Open", "Done", "High", "Medium", "Low"].map((x) => <Chip key={x} label={x} active={f === x} onPress={() => setF(x)} testID={`taskf-${x.toLowerCase()}`} />)}
      </ChipRow>
      {isLoading ? <Loading /> : isError ? <ErrorState onRetry={refetch} /> : (
        <FlatList
          data={list}
          keyExtractor={(i) => i.id}
          contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 80, flexGrow: 1 }}
          refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={colors.brandPrimary} />}
          ListEmptyComponent={<Empty icon="checkbox-marked-circle-outline" title="No tasks" subtitle="Create a task or convert one from an email." />}
          renderItem={({ item }) => (
            <Card style={{ marginBottom: 10, flexDirection: "row", gap: 12, alignItems: "center" }}>
              <Pressable testID={`task-toggle-${item.id}`} onPress={() => save.mutate({ ...item, done: !item.done })}>
                <Icon name={item.done ? "checkbox-marked-circle" : "checkbox-blank-circle-outline"} size={26} color={item.done ? colors.success : colors.muted} />
              </Pressable>
              <View style={{ flex: 1 }}>
                <Text style={{ fontSize: 15, fontWeight: "700", color: colors.onSurface, textDecorationLine: item.done ? "line-through" : "none", opacity: item.done ? 0.5 : 1 }}>{item.title}</Text>
                <View style={{ flexDirection: "row", gap: 8, marginTop: 6, alignItems: "center", flexWrap: "wrap" }}>
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
                    <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: PRIOS[item.priority] }} />
                    <T size={12} color={colors.muted}>{item.priority}</T>
                  </View>
                  {item.due ? <T size={12} color={colors.muted}>· due {new Date(item.due).toLocaleDateString([], { day: "numeric", month: "short" })}</T> : null}
                  {(item.labels || []).map((l: string) => <Badge key={l} label={l} tone="soft" />)}
                </View>
                {item.source ? <T size={11} color={colors.muted} style={{ marginTop: 4 }}>{item.source}</T> : null}
              </View>
              <Pressable testID={`task-del-${item.id}`} onPress={() => del.mutate(item.id)}><Icon name="close" size={20} color={colors.muted} /></Pressable>
            </Card>
          )}
        />
      )}
      <Pressable testID="task-fab" onPress={() => setOpen(true)} style={{ position: "absolute", right: 20, bottom: insets.bottom + 16, width: 58, height: 58, borderRadius: 20, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", elevation: 6 }}>
        <Icon name="plus" size={28} color="#fff" />
      </Pressable>
      <Sheet visible={open} onClose={() => setOpen(false)} title="New task" testID="task-sheet">
        <Field placeholder="Task title" value={title} onChangeText={setTitle} testID="task-title" />
        <T size={13} weight="700" color={colors.muted} style={{ marginTop: 14, marginBottom: 8 }}>PRIORITY</T>
        <View style={{ flexDirection: "row", gap: 8 }}>
          {["low", "medium", "high"].map((p) => (
            <Pressable key={p} onPress={() => setPriority(p)} style={{ flex: 1, paddingVertical: 12, borderRadius: radius.md, alignItems: "center", backgroundColor: priority === p ? PRIOS[p] : colors.surfaceTertiary }}>
              <Text style={{ color: priority === p ? "#fff" : colors.onSurfaceTertiary, fontWeight: "700" }}>{p}</Text>
            </Pressable>
          ))}
        </View>
        <Button title="Add task" icon="plus" testID="task-save" onPress={() => { if (title.trim()) { save.mutate({ title, priority, labels: [] }); setTitle(""); setOpen(false); } }} style={{ marginTop: 20 }} />
      </Sheet>
    </View>
  );
}
