import React from "react";
import { View, Text, Pressable, ScrollView } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useTheme, spacing } from "@/src/theme";
import { Icon, Avatar } from "@/src/ui";
import { useAuth } from "@/src/auth";

export function Header({ title, subtitle, right, showSearch = true, showMenu = false, back = false }:
  { title: string; subtitle?: string; right?: React.ReactNode; showSearch?: boolean; showMenu?: boolean; back?: boolean }) {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { colors } = useTheme();
  const { user } = useAuth();
  return (
    <View style={{ paddingTop: insets.top + 6, paddingHorizontal: spacing.lg, paddingBottom: 12, backgroundColor: colors.surface }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 10, flex: 1 }}>
          {back ? (
            <Pressable onPress={() => router.back()} testID="header-back" hitSlop={10}><Icon name="arrow-left" size={26} /></Pressable>
          ) : null}
          <View style={{ flex: 1 }}>
            <Text numberOfLines={1} style={{ fontSize: 26, fontWeight: "900", color: colors.onSurface, letterSpacing: -0.6 }}>{title}</Text>
            {subtitle ? <Text numberOfLines={1} style={{ fontSize: 13, color: colors.muted, marginTop: 2 }}>{subtitle}</Text> : null}
          </View>
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 14 }}>
          {right}
          {showSearch ? (
            <Pressable onPress={() => router.push("/search")} testID="header-search" hitSlop={10}><Icon name="magnify" size={25} color={colors.onSurface} /></Pressable>
          ) : null}
          {showMenu ? (
            <Pressable onPress={() => router.push("/settings")} testID="header-profile" hitSlop={10}>
              <Avatar name={user?.name || "U"} size={34} uri={user?.photo} />
            </Pressable>
          ) : null}
        </View>
      </View>
    </View>
  );
}

export function ChipRow({ children }: { children: React.ReactNode }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ maxHeight: 56 }}
      contentContainerStyle={{ gap: 8, paddingHorizontal: spacing.lg, paddingVertical: 10, alignItems: "center" }}>
      {children}
    </ScrollView>
  );
}
