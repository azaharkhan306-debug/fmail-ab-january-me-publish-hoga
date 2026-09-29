import { Redirect } from "expo-router";
import { View } from "react-native";
import { useAuth } from "@/src/auth";
import { Loading } from "@/src/ui";
import { useTheme } from "@/src/theme";

export default function Index() {
  const { user, loading } = useAuth();
  const { colors } = useTheme();
  if (loading) return null;
  return <Redirect href={user ? "/(tabs)" : "/(auth)/welcome"} />;
}
