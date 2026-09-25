import React from "react";
import { View, ScrollView } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing } from "@/src/theme";
import { Icon, T, Card, Loading, Empty } from "@/src/ui";
import { Header } from "@/src/screen";
import { timeAgo } from "./(tabs)/mail";

const ICON: Record<string, string> = { You: "account-outline", "Fmail AI": "brain" };

export default function Audit() {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();
  const { data, isLoading } = useQuery({ queryKey: ["audit"], queryFn: () => api.get("/audit") });

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="AI Activity" subtitle="Every important action, logged" back showSearch={false} />
      {isLoading ? <Loading /> : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 20, flexGrow: 1 }}>
          {(data || []).length === 0 ? <Empty icon="history" title="No activity yet" /> :
            (data || []).map((a: any, i: number) => (
              <View key={a.id} style={{ flexDirection: "row", gap: 12, marginBottom: 4 }}>
                <View style={{ alignItems: "center" }}>
                  <View style={{ width: 34, height: 34, borderRadius: 17, backgroundColor: a.actor === "Fmail AI" ? colors.brandTertiary : colors.surfaceTertiary, alignItems: "center", justifyContent: "center" }}>
                    <Icon name={ICON[a.actor] || "circle-small"} size={18} color={a.actor === "Fmail AI" ? colors.brandPrimary : colors.muted} />
                  </View>
                  {i < (data.length - 1) ? <View style={{ width: 2, flex: 1, backgroundColor: colors.divider, marginVertical: 2 }} /> : null}
                </View>
                <View style={{ flex: 1, paddingBottom: 16 }}>
                  <T size={14} weight="700">{a.action}</T>
                  {a.detail ? <T size={13} color={colors.muted}>{a.detail}</T> : null}
                  <T size={11} color={colors.muted} style={{ marginTop: 2 }}>{a.actor} · {timeAgo(a.created_at)} ago</T>
                </View>
              </View>
            ))}
        </ScrollView>
      )}
    </View>
  );
}
