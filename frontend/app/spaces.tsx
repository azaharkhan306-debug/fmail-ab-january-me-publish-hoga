import React, { useState } from "react";
import { View, Text, ScrollView, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Button, Loading, Sheet, Field } from "@/src/ui";
import { Header } from "@/src/screen";

const COLORS = ["#FF5E00", "#2F6FED", "#1E9E5A", "#C98A00", "#9A6BFF", "#D64545", "#00A6A6"];

export default function Spaces() {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(""); const [color, setColor] = useState(COLORS[0]);

  const { data, isLoading } = useQuery({ queryKey: ["spaces"], queryFn: () => api.get("/spaces") });
  const save = useMutation({ mutationFn: (b: any) => api.post("/spaces", b), onSuccess: () => { qc.invalidateQueries({ queryKey: ["spaces"] }); setOpen(false); setName(""); } });

  const MODULES = [
    { icon: "email-outline", label: "Emails" }, { icon: "video-outline", label: "Meetings" },
    { icon: "checkbox-marked-circle-outline", label: "Tasks" }, { icon: "folder-outline", label: "Files" },
    { icon: "calendar-outline", label: "Events" }, { icon: "brain", label: "Memory" },
  ];

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Spaces & Rooms" subtitle="Organize your world" back showSearch={false} />
      {isLoading ? <Loading /> : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 80 }}>
          <T size={13} color={colors.muted} style={{ marginBottom: 12 }}>Each space connects emails, meetings, tasks, files, events, AI memory and agents.</T>
          {(data || []).map((s: any) => (
            <Card key={s.id} style={{ marginBottom: 10 }}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 12 }}>
                <View style={{ width: 42, height: 42, borderRadius: 12, backgroundColor: s.color + "22", alignItems: "center", justifyContent: "center" }}>
                  <Icon name="shape" size={22} color={s.color} />
                </View>
                <T size={16} weight="800">{s.name}</T>
              </View>
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
                {MODULES.map((m) => (
                  <View key={m.label} style={{ flexDirection: "row", alignItems: "center", gap: 5, backgroundColor: colors.surfaceTertiary, paddingHorizontal: 10, paddingVertical: 6, borderRadius: radius.pill }}>
                    <Icon name={m.icon} size={14} color={colors.muted} />
                    <Text style={{ fontSize: 12, color: colors.onSurfaceTertiary, fontWeight: "600" }}>{m.label}</Text>
                  </View>
                ))}
              </View>
            </Card>
          ))}
        </ScrollView>
      )}
      <Pressable testID="space-fab" onPress={() => setOpen(true)} style={{ position: "absolute", right: 20, bottom: insets.bottom + 16, width: 58, height: 58, borderRadius: 20, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", elevation: 6 }}>
        <Icon name="plus" size={28} color="#fff" />
      </Pressable>
      <Sheet visible={open} onClose={() => setOpen(false)} title="New space" testID="space-sheet">
        <Field placeholder="Space name (e.g. Clients)" value={name} onChangeText={setName} testID="space-name" />
        <T size={13} weight="700" color={colors.muted} style={{ marginTop: 14, marginBottom: 8 }}>COLOR</T>
        <View style={{ flexDirection: "row", gap: 10 }}>
          {COLORS.map((c) => <Pressable key={c} onPress={() => setColor(c)} style={{ width: 38, height: 38, borderRadius: 19, backgroundColor: c, borderWidth: color === c ? 3 : 0, borderColor: colors.onSurface }} />)}
        </View>
        <Button title="Create space" icon="plus" testID="space-save" onPress={() => { if (name.trim()) save.mutate({ name, color }); }} style={{ marginTop: 20 }} />
      </Sheet>
    </View>
  );
}
