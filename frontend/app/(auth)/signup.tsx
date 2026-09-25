import React, { useState } from "react";
import { View, Text, Pressable } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useAuth } from "@/src/auth";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, Button, Field, T } from "@/src/ui";

export default function Signup() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { signup } = useAuth();
  const { colors } = useTheme();
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onSignup = async () => {
    setError("");
    if (!name || !username || !email || !password) return setError("Please fill in all fields.");
    if (password.length < 6) return setError("Password must be at least 6 characters.");
    setLoading(true);
    try {
      await signup(email.trim(), password, name.trim(), username.trim());
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
        <Text style={{ fontSize: 30, fontWeight: "900", color: colors.onSurface, letterSpacing: -0.5 }}>Create identity</Text>
        <T size={15} color={colors.muted} style={{ marginTop: 6, marginBottom: 28 }}>Your unified communication home</T>

        <View style={{ gap: 12 }}>
          <Field icon="account-outline" placeholder="Full name" value={name} onChangeText={setName} testID="signup-name" />
          <View>
            <Field icon="at" placeholder="username" value={username} onChangeText={(t: string) => setUsername(t.replace(/[^a-z0-9._]/gi, "").toLowerCase())} autoCapitalize="none" testID="signup-username" />
            {username ? (
              <View style={{ backgroundColor: colors.brandTertiary, alignSelf: "flex-start", paddingHorizontal: 12, paddingVertical: 5, borderRadius: radius.sm, marginTop: 6 }}>
                <Text style={{ color: colors.onBrandTertiary, fontWeight: "700", fontSize: 13 }}>{username}@fmails.in</Text>
              </View>
            ) : null}
          </View>
          <Field icon="email-outline" placeholder="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" testID="signup-email" />
          <Field icon="lock-outline" placeholder="Password (min 6 chars)" value={password} onChangeText={setPassword} secureTextEntry testID="signup-password" />
        </View>

        {error ? <Text style={{ color: colors.error, marginTop: 12 }} testID="signup-error">{error}</Text> : null}

        <Button title="Create my Fmail" onPress={onSignup} loading={loading} testID="signup-submit" style={{ marginTop: 24 }} />

        <Pressable onPress={() => router.replace("/(auth)/login")} style={{ marginTop: 20, alignItems: "center" }} testID="go-login">
          <T color={colors.muted}>Already have an account? <Text style={{ color: colors.brandPrimary, fontWeight: "700" }}>Sign in</Text></T>
        </Pressable>
      </KeyboardAwareScrollView>
    </View>
  );
}
