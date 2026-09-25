import { Redirect } from "expo-router";
import { View } from "react-native";
import { useAuth } from "@/src/auth";
import { Loading } from "@/src/ui";
import { useTheme } from "@/src/theme";

export default function Index() {
  const { user, loading } = useAuth();
  const { colors } = useTheme();
  if (loading) {
    return <View style={{ flex: 1, backgroundColor: colors.surface }}><Loading label="Fmail" /></View>;
  }
  return <Redirect href={user ? "/(tabs)" : "/(auth)/welcome"} />;
}
