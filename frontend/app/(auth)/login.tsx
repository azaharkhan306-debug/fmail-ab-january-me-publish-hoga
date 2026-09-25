import React, { useState } from "react";
import { View, Text, Pressable } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useAuth } from "@/src/auth";
import { useTheme, spacing } from "@/src/theme";
import { Icon, Button, Field, T } from "@/src/ui";

export default function Login() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { login } = useAuth();
  const { colors } = useTheme();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onLogin = async () => {
    setError("");
    if (!email || !password) return setError("Please enter your email and password.");
    setLoading(true);
    try {
      await login(email.trim(), password);
      router.replace("/(tabs)");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <KeyboardAwareScrollView contentContainerStyle={{ paddingTop: insets.top + 20, paddingBottom: 40, paddingHorizontal: spacing.xl }} bottomOffset={20}>
        <Pressable onPress={() => router.back()} style={{ marginBottom: 20 }}><Icon name="arrow-left" size={26} /></Pressable>
        <Text style={{ fontSize: 30, fontWeight: "900", color: colors.onSurface, letterSpacing: -0.5 }}>Welcome back</Text>
        <T size={15} color={colors.muted} style={{ marginTop: 6, marginBottom: 28 }}>Sign in to your Fmail account</T>

        <View style={{ gap: 12 }}>
          <Field icon="email-outline" placeholder="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" testID="login-email" />
          <Field icon="lock-outline" placeholder="Password" value={password} onChangeText={setPassword} secureTextEntry testID="login-password" />
        </View>

        {error ? <Text style={{ color: colors.error, marginTop: 12 }} testID="login-error">{error}</Text> : null}

        <Button title="Sign in" onPress={onLogin} loading={loading} testID="login-submit" style={{ marginTop: 24 }} />

        <Pressable onPress={() => router.replace("/(auth)/signup")} style={{ marginTop: 20, alignItems: "center" }} testID="go-signup">
          <T color={colors.muted}>New to Fmail? <Text style={{ color: colors.brandPrimary, fontWeight: "700" }}>Create identity</Text></T>
        </Pressable>
      </KeyboardAwareScrollView>
    </View>
  );
}
