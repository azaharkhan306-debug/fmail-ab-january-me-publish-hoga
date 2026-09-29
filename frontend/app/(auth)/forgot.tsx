import React, { useState, useEffect } from "react";
import { View, Text, Pressable } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { api, setToken } from "@/src/api";
import { useAuth } from "@/src/auth";
import { useTheme, spacing } from "@/src/theme";
import { Icon, Button, Field, T } from "@/src/ui";

export default function Forgot() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { setUser } = useAuth();
  const { colors } = useTheme();
  const [step, setStep] = useState<"email" | "reset">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => (c <= 1 ? 0 : c - 1)), 1000);
    return () => clearInterval(t);
  }, [cooldown]);

  const sendCode = async () => {
    setError(""); setInfo("");
    if (!email.trim()) return setError("Please enter your account email.");
    setLoading(true);
    try {
      const r = await api.post("/auth/request-otp", { email: email.trim(), purpose: "reset" });
      setStep("reset");
      setCooldown(30);
      if (r.delivered) setInfo(`If an account exists, we sent a reset code to ${email.trim()}.`);
      else setInfo("If an account exists, a reset email was sent.");
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  const resend = async () => {
    if (cooldown > 0) return;
    try {
      const r = await api.post("/auth/request-otp", { email: email.trim(), purpose: "reset" });
      setCooldown(30);
      setInfo(r.delivered ? "A new code was sent." : "If an account exists, a new reset email was sent.");
    } catch (e: any) { setError(e.message); }
  };

  const doReset = async () => {
    setError("");
    if (!code || code.length < 4) return setError("Please enter the reset code.");
    if (password.length < 6) return setError("New password must be at least 6 characters.");
    setLoading(true);
    try {
      const r = await api.post("/auth/reset-password", { email: email.trim(), code: code.trim(), password });
      await setToken(r.token);
      setUser(r.user);
      router.replace("/(tabs)");
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <KeyboardAwareScrollView contentContainerStyle={{ paddingTop: insets.top + 20, paddingBottom: 40, paddingHorizontal: spacing.xl }} bottomOffset={20} keyboardShouldPersistTaps="handled">
        <Pressable onPress={() => (step === "reset" ? setStep("email") : router.back())} style={{ marginBottom: 20 }}><Icon name="arrow-left" size={26} /></Pressable>
        <Text style={{ fontSize: 30, fontWeight: "900", color: colors.onSurface, letterSpacing: -0.5 }}>Reset password</Text>
        <T size={15} color={colors.muted} style={{ marginTop: 6, marginBottom: 24 }}>
          {step === "email" ? "We'll send a verification code to your email." : (info || "Enter the code and your new password.")}
        </T>

        {step === "email" ? (
          <>
            <Field icon="email-outline" placeholder="Account email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" testID="forgot-email" />
            {error ? <Text style={{ color: colors.error, marginTop: 12 }} testID="forgot-error">{error}</Text> : null}
            <Button title="Send code" onPress={sendCode} loading={loading} testID="forgot-send" style={{ marginTop: 20 }} />
          </>
        ) : (
          <>
            <Field icon="shield-check-outline" placeholder="Reset code" value={code} onChangeText={(t: string) => setCode(t.replace(/[^0-9]/g, "").slice(0, 6))} keyboardType="number-pad" testID="forgot-code" />
            <View style={{ height: 12 }} />
            <Field icon="lock-outline" placeholder="New password (min 6 chars)" value={password} onChangeText={setPassword} secureTextEntry testID="forgot-password" />
            {error ? <Text style={{ color: colors.error, marginTop: 12 }} testID="forgot-error">{error}</Text> : null}
            <Button title="Reset & sign in" onPress={doReset} loading={loading} testID="forgot-reset" style={{ marginTop: 20 }} />
            <Pressable onPress={resend} disabled={cooldown > 0} style={{ marginTop: 18, alignItems: "center" }} testID="forgot-resend">
              <T color={cooldown > 0 ? colors.muted : colors.brandPrimary}>{cooldown > 0 ? `Resend code in ${cooldown}s` : "Resend code"}</T>
            </Pressable>
          </>
        )}
      </KeyboardAwareScrollView>
    </View>
  );
}
