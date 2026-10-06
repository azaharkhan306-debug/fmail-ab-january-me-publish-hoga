import React, { useState, useEffect } from "react";
import { View, Text, Pressable } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useAuth } from "@/src/auth";
import { api } from "@/src/api";
import { useTheme, spacing } from "@/src/theme";
import { Icon, Button, Field, T } from "@/src/ui";

export default function Signup() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { signup, loginWithGoogle } = useAuth();
  const { colors } = useTheme();
  const [step, setStep] = useState<"form" | "otp">("form");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => (c <= 1 ? 0 : c - 1)), 1000);
    return () => clearInterval(t);
  }, [cooldown]);

  const onGoogle = async () => {
    setError("");
    setGoogleLoading(true);
    try {
      await loginWithGoogle();
      router.replace("/(tabs)");
    } catch (e: any) {
      setError(e?.message || "Google sign-in failed. Please try again.");
    } finally {
      setGoogleLoading(false);
    }
  };

  const onCreate = async () => {
    setError(""); setInfo("");
    if (!name || !email || !password) return setError("Please fill in all fields.");
    if (password.length < 6) return setError("Password must be at least 6 characters.");
    setLoading(true);
    try {
      await signup(email.trim(), password, name.trim());
      router.replace("/(tabs)");
    } catch (e: any) {
      // If the server requires email verification, move to the OTP step.
      if (/verify|code/i.test(e?.message || "")) {
        try {
          const r = await api.post("/auth/request-otp", { email: email.trim(), purpose: "signup" });
          setStep("otp");
          setCooldown(30);
          setInfo(r?.delivered ? `We sent a 6-digit code to ${email.trim()}.` : "Enter the verification code we sent.");
        } catch (err: any) {
          setError(err?.message || e.message);
        }
      } else {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const onVerify = async () => {
    setError("");
    if (!code || code.length < 4) return setError("Please enter the verification code.");
    setLoading(true);
    try {
      await signup(email.trim(), password, name.trim(), code.trim());
      router.replace("/(tabs)");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const resend = async () => {
    if (cooldown > 0) return;
    try {
      const r = await api.post("/auth/request-otp", { email: email.trim(), purpose: "signup" });
      setCooldown(30);
      setInfo(r?.delivered ? "A new code was sent." : "A new verification email was sent.");
    } catch (e: any) { setError(e.message); }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <KeyboardAwareScrollView contentContainerStyle={{ paddingTop: insets.top + 20, paddingBottom: 40, paddingHorizontal: spacing.xl }} bottomOffset={20} keyboardShouldPersistTaps="handled">
        <Pressable onPress={() => (step === "otp" ? setStep("form") : router.back())} style={{ marginBottom: 20 }}><Icon name="arrow-left" size={26} /></Pressable>

        {step === "form" ? (
          <>
            <Text style={{ fontSize: 30, fontWeight: "900", color: colors.onSurface, letterSpacing: -0.5 }}>Create your account</Text>
            <T size={15} color={colors.muted} style={{ marginTop: 6, marginBottom: 24 }}>Connect your Gmail after signup to manage your real inbox with AI.</T>

            <Button title="Continue with Google" icon="google" testID="signup-google" loading={googleLoading} onPress={onGoogle} />
            <View style={{ flexDirection: "row", alignItems: "center", gap: 10, marginVertical: 20 }}>
              <View style={{ flex: 1, height: 1, backgroundColor: colors.border }} />
              <T size={12} color={colors.muted}>or sign up with email</T>
              <View style={{ flex: 1, height: 1, backgroundColor: colors.border }} />
            </View>

            <View style={{ gap: 12 }}>
              <Field icon="account-outline" placeholder="Full name" value={name} onChangeText={setName} testID="signup-name" />
              <Field icon="email-outline" placeholder="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" testID="signup-email" />
              <Field icon="lock-outline" placeholder="Password (min 6 chars)" value={password} onChangeText={setPassword} secureTextEntry testID="signup-password" />
            </View>

            {error ? <Text style={{ color: colors.error, marginTop: 12 }} testID="signup-error">{error}</Text> : null}
            <Button title="Create account" onPress={onCreate} loading={loading} testID="signup-continue" style={{ marginTop: 24 }} />

            <Pressable onPress={() => router.replace("/(auth)/login")} style={{ marginTop: 20, alignItems: "center" }} testID="go-login">
              <T color={colors.muted}>Already have an account? <Text style={{ color: colors.brandPrimary, fontWeight: "700" }}>Sign in</Text></T>
            </Pressable>
          </>
        ) : (
          <>
            <Text style={{ fontSize: 30, fontWeight: "900", color: colors.onSurface, letterSpacing: -0.5 }}>Verify email</Text>
            <T size={15} color={colors.muted} style={{ marginTop: 6, marginBottom: 20 }}>{info || `Enter the code sent to ${email}`}</T>
            <Field icon="shield-check-outline" placeholder="6-digit code" value={code} onChangeText={(t: string) => setCode(t.replace(/[^0-9]/g, "").slice(0, 6))} keyboardType="number-pad" testID="signup-otp" />
            {error ? <Text style={{ color: colors.error, marginTop: 12 }} testID="signup-error">{error}</Text> : null}
            <Button title="Create my account" onPress={onVerify} loading={loading} testID="signup-submit" style={{ marginTop: 20 }} />
            <Pressable onPress={resend} disabled={cooldown > 0} style={{ marginTop: 18, alignItems: "center" }} testID="resend-otp">
              <T color={cooldown > 0 ? colors.muted : colors.brandPrimary}>{cooldown > 0 ? `Resend code in ${cooldown}s` : "Resend code"}</T>
            </Pressable>
          </>
        )}
      </KeyboardAwareScrollView>
    </View>
  );
}
