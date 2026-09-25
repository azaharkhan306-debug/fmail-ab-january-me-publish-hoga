import React, { useState } from "react";
import { View, Text, FlatList, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as DocumentPicker from "expo-document-picker";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Button, Loading, ErrorState, Empty, Sheet } from "@/src/ui";
import { Header } from "@/src/screen";

const ICONS: Record<string, string> = { pdf: "file-pdf-box", presentation: "file-powerpoint-box", design: "palette-outline", document: "file-document-outline", image: "file-image-outline", spreadsheet: "file-excel-box" };

export default function Files() {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const [sel, setSel] = useState<any>(null);

  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["files"], queryFn: () => api.get("/files") });
  const summarize = useMutation({
    mutationFn: (fid: string) => api.post(`/ai/file-summary/${fid}`),
    onSuccess: (r) => { setSel((s: any) => ({ ...s, summary: r.summary })); qc.invalidateQueries({ queryKey: ["files"] }); },
  });

  const pick = async () => {
    try {
      const res = await DocumentPicker.getDocumentAsync({ type: "*/*", copyToCacheDirectory: true });
      if (res.canceled) return;
      const a = res.assets[0];
      const form = new FormData();
      form.append("name", a.name);
      form.append("type", a.mimeType?.includes("pdf") ? "pdf" : a.mimeType?.includes("image") ? "image" : "document");
      form.append("size", a.size ? `${Math.round(a.size / 1024)} KB` : "");
      await api.upload("/files", form);
      qc.invalidateQueries({ queryKey: ["files"] });
    } catch {}
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Files" back showSearch={false} />
      {isLoading ? <Loading /> : isError ? <ErrorState onRetry={refetch} /> : (
        <FlatList
          data={data || []}
          keyExtractor={(i) => i.id}
          contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 80, flexGrow: 1 }}
          ListEmptyComponent={<Empty icon="folder-outline" title="No files" subtitle="Upload a document to get started." />}
          renderItem={({ item }) => (
            <Card testID={`file-${item.id}`} onPress={() => setSel(item)} style={{ marginBottom: 10, flexDirection: "row", gap: 12, alignItems: "center" }}>
              <View style={{ width: 46, height: 46, borderRadius: 12, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" }}>
                <Icon name={ICONS[item.type] || "file-outline"} size={24} color={colors.brandPrimary} />
              </View>
              <View style={{ flex: 1 }}>
                <T size={15} weight="700" numberOfLines={1}>{item.name}</T>
                <T size={12} color={colors.muted}>{item.size}{item.source ? ` · ${item.source}` : ""}</T>
              </View>
              {item.summary ? <Icon name="brain" size={20} color={colors.success} /> : null}
            </Card>
          )}
        />
      )}
      <Pressable testID="file-fab" onPress={pick} style={{ position: "absolute", right: 20, bottom: insets.bottom + 16, width: 58, height: 58, borderRadius: 20, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", elevation: 6 }}>
        <Icon name="upload" size={26} color="#fff" />
      </Pressable>

      <Sheet visible={!!sel} onClose={() => setSel(null)} title={sel?.name} testID="file-sheet">
        {sel ? (
          <>
            <View style={{ alignItems: "center", marginBottom: 16 }}>
              <View style={{ width: 70, height: 70, borderRadius: 18, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" }}>
                <Icon name={ICONS[sel.type] || "file-outline"} size={36} color={colors.brandPrimary} />
              </View>
              <T size={13} color={colors.muted} style={{ marginTop: 8 }}>{sel.type.toUpperCase()} · {sel.size}</T>
            </View>
            {sel.summary ? (
              <Card style={{ backgroundColor: colors.brandTertiary, borderColor: colors.brandPrimary + "33" }}>
                <View style={{ flexDirection: "row", alignItems: "center", gap: 6, marginBottom: 6 }}>
                  <Icon name="brain" size={16} color={colors.brandPrimary} />
                  <T size={12} weight="800" color={colors.onBrandTertiary}>ATTACHMENT BRAIN</T>
                </View>
                <T size={14} color={colors.onBrandTertiary} style={{ lineHeight: 21 }}>{sel.summary}</T>
              </Card>
            ) : (
              <Button title="Summarize with AI" icon="auto-fix" testID="file-summarize" loading={summarize.isPending} onPress={() => summarize.mutate(sel.id)} />
            )}
          </>
        ) : null}
      </Sheet>
    </View>
  );
}
