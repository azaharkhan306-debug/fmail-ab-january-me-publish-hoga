import React, { useState } from "react";
import { View, Text, FlatList, Pressable } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Button, Loading, ErrorState, Empty, Avatar, Badge, Sheet, Field } from "@/src/ui";
import { Header } from "@/src/screen";

export default function Contacts() {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [graph, setGraph] = useState<any>(null);
  const [name, setName] = useState(""); const [email, setEmail] = useState(""); const [company, setCompany] = useState("");

  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["contacts"], queryFn: () => api.get("/contacts") });
  const save = useMutation({ mutationFn: (b: any) => api.post("/contacts", b), onSuccess: () => { qc.invalidateQueries({ queryKey: ["contacts"] }); setOpen(false); setName(""); setEmail(""); setCompany(""); } });

  const openGraph = async (c: any) => {
    try { const g = await api.get(`/contacts/${c.id}/graph`); setGraph(g); } catch {}
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Contacts" back showSearch={false} />
      {isLoading ? <Loading /> : isError ? <ErrorState onRetry={refetch} /> : (
        <FlatList
          data={data || []}
          keyExtractor={(i) => i.id}
          contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 80, flexGrow: 1 }}
          ListEmptyComponent={<Empty icon="account-group-outline" title="No contacts" />}
          renderItem={({ item }) => (
            <Card testID={`contact-${item.id}`} onPress={() => openGraph(item)} style={{ marginBottom: 10, flexDirection: "row", gap: 12, alignItems: "center" }}>
              <Avatar name={item.name} size={46} />
              <View style={{ flex: 1 }}>
                <T size={15} weight="700">{item.name}</T>
                <T size={13} color={colors.muted}>{item.role ? item.role + " · " : ""}{item.company || item.email}</T>
              </View>
              <Icon name="graph-outline" size={22} color={colors.brandPrimary} />
            </Card>
          )}
        />
      )}
      <Pressable testID="contact-fab" onPress={() => setOpen(true)} style={{ position: "absolute", right: 20, bottom: insets.bottom + 16, width: 58, height: 58, borderRadius: 20, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", elevation: 6 }}>
        <Icon name="account-plus" size={26} color="#fff" />
      </Pressable>

      <Sheet visible={open} onClose={() => setOpen(false)} title="New contact" testID="contact-sheet">
        <View style={{ gap: 12 }}>
          <Field icon="account-outline" placeholder="Name" value={name} onChangeText={setName} testID="contact-name" />
          <Field icon="email-outline" placeholder="Email" value={email} onChangeText={setEmail} autoCapitalize="none" testID="contact-email" />
          <Field icon="office-building-outline" placeholder="Company" value={company} onChangeText={setCompany} testID="contact-company" />
        </View>
        <Button title="Save contact" icon="content-save-outline" testID="contact-save" onPress={() => { if (name.trim() && email.trim()) save.mutate({ name, email, company }); }} style={{ marginTop: 20 }} />
      </Sheet>

      <Sheet visible={!!graph} onClose={() => setGraph(null)} title="Communication Graph" testID="graph-sheet">
        {graph ? (
          <>
            <View style={{ alignItems: "center", marginBottom: 16 }}>
              <Avatar name={graph.contact.name} size={64} />
              <T size={18} weight="800" style={{ marginTop: 10 }}>{graph.contact.name}</T>
              <T size={13} color={colors.muted}>{graph.contact.role} · {graph.contact.company}</T>
            </View>
            <GraphSection icon="email-outline" label="Emails" count={graph.emails.length} items={graph.emails.map((e: any) => e.subject)} />
            <GraphSection icon="video-outline" label="Meetings" count={graph.meetings.length} items={graph.meetings.map((m: any) => m.title)} />
            <GraphSection icon="checkbox-marked-circle-outline" label="Tasks" count={graph.tasks.length} items={graph.tasks.map((t: any) => t.title)} />
            <GraphSection icon="brain" label="Memory" count={graph.memory.length} items={graph.memory.map((m: any) => m.detail)} />
          </>
        ) : null}
      </Sheet>
    </View>
  );
}

function GraphSection({ icon, label, count, items }: { icon: any; label: string; count: number; items: string[] }) {
  const { colors } = useTheme();
  return (
    <Card style={{ marginBottom: 10 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginBottom: items.length ? 8 : 0 }}>
        <Icon name={icon} size={18} color={colors.brandPrimary} />
        <T size={14} weight="800">{label}</T>
        <Badge label={String(count)} tone="soft" />
      </View>
      {items.slice(0, 4).map((it, i) => (
        <View key={i} style={{ flexDirection: "row", gap: 8, marginBottom: 4 }}>
          <Text style={{ color: colors.brandPrimary }}>•</Text>
          <T size={13} color={colors.onSurfaceTertiary} style={{ flex: 1 }} numberOfLines={1}>{it}</T>
        </View>
      ))}
    </Card>
  );
}
