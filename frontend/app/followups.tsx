import React from "react";
import { View, Text, ScrollView, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing } from "@/src/theme";
import { Icon, T, Card, Button, Loading, Empty, Avatar } from "@/src/ui";
import { Header } from "@/src/screen";

export default function Followups() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["followups"], queryFn: () => api.get("/followups") });
  const act = useMutation({ mutationFn: ({ id, a }: any) => api.post(`/followups/${id}/${a}`), onSuccess: () => qc.invalidateQueries({ queryKey: ["followups"] }) });

  const open = (data || []).filter((f: any) => f.status === "open");

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Follow-up Brain" subtitle="Conversations waiting on a reply" back showSearch={false} />
      {isLoading ? <Loading /> : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 20, flexGrow: 1 }}>
          {open.length === 0 ? <Empty icon="check-all" title="All caught up" subtitle="No conversations are waiting on a reply." /> :
            open.map((f: any) => (
              <Card key={f.id} style={{ marginBottom: 12 }}>
                <View style={{ flexDirection: "row", gap: 12, alignItems: "center", marginBottom: 12 }}>
                  <Avatar name={f.person} size={44} />
                  <View style={{ flex: 1 }}>
                    <T size={15} weight="700">Waiting for {f.person}</T>
                    <T size={13} color={colors.muted} numberOfLines={1}>{f.subject}</T>
                  </View>
                  <View style={{ backgroundColor: "#C98A0022", paddingHorizontal: 10, paddingVertical: 5, borderRadius: 10 }}>
                    <Text style={{ color: "#C98A00", fontWeight: "800", fontSize: 12 }}>{f.days}d</Text>
                  </View>
                </View>
                <View style={{ flexDirection: "row", gap: 8 }}>
                  <Button title="Follow up" icon="send" small style={{ flex: 1 }} testID={`fu-send-${f.id}`} onPress={() => { if (f.threadId) router.push(`/thread/${f.threadId}`); else act.mutate({ id: f.id, a: "done" }); }} />
                  <Button title="Ignore" variant="ghost" small testID={`fu-ignore-${f.id}`} onPress={() => act.mutate({ id: f.id, a: "ignored" })} />
                </View>
              </Card>
            ))}
        </ScrollView>
      )}
    </View>
  );
}
