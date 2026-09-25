import React, { useState } from "react";
import { View, Text, FlatList, Pressable, RefreshControl } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Loading, ErrorState, Empty, Avatar, Badge, Chip, Sheet } from "@/src/ui";
import { Header, ChipRow } from "@/src/screen";

const FOLDERS: { key: string; label: string; icon: any }[] = [
  { key: "inbox", label: "Inbox", icon: "inbox" },
  { key: "important", label: "Important", icon: "label-outline" },
  { key: "starred", label: "Starred", icon: "star-outline" },
  { key: "sent", label: "Sent", icon: "send-outline" },
  { key: "drafts", label: "Drafts", icon: "file-document-edit-outline" },
  { key: "archive", label: "Archive", icon: "archive-outline" },
  { key: "trash", label: "Trash", icon: "trash-can-outline" },
];
const FILTERS = ["All", "Unread", "Important"];
const CATEGORIES = ["Work", "Personal", "Finance", "Shopping", "College", "Startup", "Newsletter", "Social"];
const ACCOUNTS: { key: string; label: string }[] = [
  { key: "fmail", label: "Fmail" }, { key: "gmail", label: "Gmail" }, { key: "outlook", label: "Outlook" },
];

const ACCOUNT_ICON: Record<string, string> = { fmail: "at", gmail: "google", outlook: "microsoft-outlook" };

export default function Mail() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const [folder, setFolder] = useState("inbox");
  const [filter, setFilter] = useState("All");
  const [category, setCategory] = useState<string | null>(null);
  const [account, setAccount] = useState<string | null>(null);
  const [folderOpen, setFolderOpen] = useState(false);

  const params = new URLSearchParams({ folder });
  if (filter === "Unread") params.set("filter", "unread");
  if (filter === "Important") params.set("filter", "important");
  if (category) params.set("category", category);
  if (account) params.set("account", account);

  const { data, isLoading, isError, refetch, isRefetching } = useQuery({
    queryKey: ["emails", folder, filter, category, account],
    queryFn: () => api.get("/emails?" + params.toString()),
  });

  const folderLabel = FOLDERS.find((f) => f.key === folder)?.label || "Inbox";

  const renderItem = ({ item }: { item: any }) => (
    <Pressable testID={`email-${item.threadId}`} onPress={() => router.push(`/thread/${item.threadId}`)}
      style={{ flexDirection: "row", gap: 12, paddingVertical: 14, paddingHorizontal: spacing.lg, backgroundColor: item.unread ? colors.brandTertiary + "55" : colors.surface, borderBottomWidth: 1, borderBottomColor: colors.divider }}>
      <View>
        <Avatar name={item.sender} size={46} />
        <View style={{ position: "absolute", right: -2, bottom: -2, width: 18, height: 18, borderRadius: 9, backgroundColor: colors.surface, alignItems: "center", justifyContent: "center" }}>
          <Icon name={ACCOUNT_ICON[item.account] || "email"} size={11} color={colors.muted} />
        </View>
      </View>
      <View style={{ flex: 1 }}>
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
          <Text numberOfLines={1} style={{ flex: 1, fontSize: 15, fontWeight: item.unread ? "800" : "600", color: colors.onSurface }}>{item.sender}</Text>
          <Text style={{ fontSize: 11, color: colors.muted, marginLeft: 8 }}>{timeAgo(item.created_at)}</Text>
        </View>
        <Text numberOfLines={1} style={{ fontSize: 14, fontWeight: item.unread ? "700" : "500", color: colors.onSurface, marginTop: 2 }}>{item.subject}</Text>
        <Text numberOfLines={1} style={{ fontSize: 13, color: colors.muted, marginTop: 2 }}>{item.snippet}</Text>
        <View style={{ flexDirection: "row", gap: 6, marginTop: 8, alignItems: "center" }}>
          <Badge label={item.aiLabel} />
          {item.suspicious ? <Badge label="Suspicious" color="#D64545" tone="solid" /> : null}
          {item.star ? <Icon name="star" size={15} color="#C98A00" /> : null}
        </View>
      </View>
    </Pressable>
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title={folderLabel} subtitle="Universal Inbox" showMenu
        right={<Pressable onPress={() => setFolderOpen(true)} testID="folder-switch" hitSlop={8}><Icon name="folder-swap-outline" size={24} /></Pressable>} />

      <ChipRow>
        {FILTERS.map((f) => <Chip key={f} label={f} active={filter === f} onPress={() => setFilter(f)} testID={`filter-${f.toLowerCase()}`} />)}
        <View style={{ width: 1, height: 22, backgroundColor: colors.border, marginHorizontal: 4 }} />
        {ACCOUNTS.map((a) => <Chip key={a.key} label={a.label} icon={ACCOUNT_ICON[a.key]} active={account === a.key} onPress={() => setAccount(account === a.key ? null : a.key)} testID={`account-${a.key}`} />)}
        {CATEGORIES.map((c) => <Chip key={c} label={c} active={category === c} onPress={() => setCategory(category === c ? null : c)} testID={`cat-${c.toLowerCase()}`} />)}
      </ChipRow>

      {isLoading ? <Loading /> : isError ? <ErrorState onRetry={refetch} /> : (
        <FlatList
          data={data || []}
          keyExtractor={(i) => i.threadId}
          renderItem={renderItem}
          ListEmptyComponent={<Empty title="Nothing here" subtitle="This view has no messages right now." />}
          contentContainerStyle={{ paddingBottom: 24, flexGrow: 1 }}
          refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={colors.brandPrimary} />}
        />
      )}

      <Pressable testID="compose-fab" onPress={() => router.push("/compose")}
        style={{ position: "absolute", right: 20, bottom: 24, width: 58, height: 58, borderRadius: 20, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", shadowColor: "#000", shadowOpacity: 0.25, shadowRadius: 8, shadowOffset: { width: 0, height: 4 }, elevation: 6 }}>
        <Icon name="pencil" size={26} color="#fff" />
      </Pressable>

      <Sheet visible={folderOpen} onClose={() => setFolderOpen(false)} title="Folders" testID="folder-sheet">
        {FOLDERS.map((f) => (
          <Pressable key={f.key} testID={`folder-${f.key}`} onPress={() => { setFolder(f.key); setCategory(null); setFilter("All"); setFolderOpen(false); }}
            style={{ flexDirection: "row", alignItems: "center", gap: 14, paddingVertical: 14 }}>
            <Icon name={f.icon} size={22} color={folder === f.key ? colors.brandPrimary : colors.muted} />
            <Text style={{ fontSize: 16, fontWeight: folder === f.key ? "800" : "500", color: folder === f.key ? colors.brandPrimary : colors.onSurface }}>{f.label}</Text>
          </Pressable>
        ))}
      </Sheet>
    </View>
  );
}

export function timeAgo(iso: string) {
  const d = new Date(iso).getTime();
  const diff = Date.now() - d;
  const h = Math.floor(diff / 3600000);
  if (h < 1) return `${Math.max(1, Math.floor(diff / 60000))}m`;
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}
