import React from "react";
import { Platform, View } from "react-native";
import { Tabs, Redirect } from "expo-router";
import MDIcon from "@react-native-vector-icons/material-design-icons";
import { useAuth } from "@/src/auth";
import { useTheme } from "@/src/theme";
import { Loading } from "@/src/ui";

export default function TabsLayout() {
  const { user, loading } = useAuth();
  const { colors } = useTheme();

  if (loading) return <View style={{ flex: 1, backgroundColor: colors.surface }}><Loading /></View>;
  if (!user) return <Redirect href="/(auth)/welcome" />;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.brandPrimary,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: {
          backgroundColor: colors.surfaceSecondary,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          ...(Platform.OS === "web" ? { height: 64 } : {}),
        },
        tabBarItemStyle: { alignSelf: "center" },
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
      }}
    >
      <Tabs.Screen name="index" options={{ title: "Home", tabBarIcon: ({ color, size }) => <MDIcon name="view-dashboard-outline" size={size} color={color} /> }} />
      <Tabs.Screen name="mail" options={{ title: "Mail", tabBarIcon: ({ color, size }) => <MDIcon name="email-outline" size={size} color={color} /> }} />
      <Tabs.Screen name="meet" options={{ title: "Meet", tabBarIcon: ({ color, size }) => <MDIcon name="video-outline" size={size} color={color} /> }} />
      <Tabs.Screen name="ask" options={{ title: "Ask Fmail", tabBarIcon: ({ color, size }) => <MDIcon name="robot-happy-outline" size={size} color={color} /> }} />
    </Tabs>
  );
}
