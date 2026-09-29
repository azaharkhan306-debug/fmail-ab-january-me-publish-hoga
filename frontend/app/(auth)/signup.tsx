import React, { useState, useEffect, useRef } from "react";
import { View, Text, Pressable, ActivityIndicator } from "react-native";
import { KeyboardAwareScrollView } from "react-native-keyboard-controller";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useAuth } from "@/src/auth";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, Button, Field, T } from "@/src/ui";

export default function Signup() {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { signup } = useAuth();
  const { colors } = useTheme();
  const [step, setStep] = useState<"form" | "otp">("form");
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  // handle availability
  const [handleState, setHandleState] = useState<{ checking: boolean; available: boolean | null; reason?: string }>({ checking: false, available: null });
  const [cooldown, setCooldown] = useState(0);
  const timer = useRef<any>(null);

  useEffect(() => {
    if (!username || username.length < 3) { setHandleState({ checking: false, available: null }); return; }
    setHandleState({ checking: true, available: null });
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      try {
        const r = await api.get(`/auth/check-handle?handle=${encodeURIComponent(username)}`);
        setHandleState({ checking: false, available: r.available, reason: r.reason });
      } catch {
        setHandleState({ checking: false, available: null });
      }
    }, 400);
    return () => timer.current && clearTimeout(timer.current);
  }, [username]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => (c <= 1 ? 0 : c - 1)), 1000);
    return () => clearInterval(t);
  }, [cooldown]);

  const requestCode = async () => {
    setError(""); setInfo("");
    if (!name || !username || !email || !password) return setError("Please fill in all fields.");
    if (password.length < 6) return setError("Password must be at least 6 characters.");
    if (handleState.available === false) return setError(handleState.reason || "This Fmail address is taken.");
    setLoading(true);
    try {
      const r = await api.post("/auth/request-otp", { email: email.trim(), purpose: "signup" });
      setStep("otp");
      setCooldown(30);
      if (r.delivered) setInfo(`We sent a 6-digit code to ${email.trim()}.`);
      else setInfo("If an account exists, a verification email was sent.");
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
      setInfo(r.delivered ? "A new code was sent." : "If an account exists, a new verification email was sent.");
    } catch (e: any) { setError(e.message); }
  };

  const onCreate = async () => {
    setError("");
    if (!code || code.length < 4) return setError("Please enter the verification code.");
    setLoading(true);
    try {
      await signup(email.trim(), password, name.trim(), username.trim(), code.trim());
      router.replace("/(tabs)");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <KeyboardAwareScrollView contentContainerStyle={{ paddingTop: insets.top + 20, paddingBottom: 40, paddingHorizontal: spacing.xl }} bottomOffset={20} keyboardShouldPersistTaps="handled">
        <Pressable onPress={() => (step === "otp" ? setStep("form") : router.back())} style={{ marginBottom: 20 }}><Icon name="arrow-left" size={26} /></Pressable>

        {step === "form" ? (
          <>
            <Text style={{ fontSize: 30, fontWeight: "900", color: colors.onSurface, letterSpacing: -0.5 }}>Create identity</Text>
            <T size={15} color={colors.muted} style={{ marginTop: 6, marginBottom: 28 }}>Your unified communication home</T>

            <View style={{ gap: 12 }}>
              <Field icon="account-outline" placeholder="Full name" value={name} onChangeText={setName} testID="signup-name" />
              <View>
                <Field icon="at" placeholder="username" value={username} onChangeText={(t: string) => setUsername(t.replace(/[^a-z0-9._-]/gi, "").toLowerCase())} autoCapitalize="none" testID="signup-username" />
                {username ? (
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 8, marginTop: 6 }}>
                    <View style={{ backgroundColor: colors.brandTertiary, paddingHorizontal: 12, paddingVertical: 5, borderRadius: radius.sm }}>
                      <Text style={{ color: colors.onBrandTertiary, fontWeight: "700", fontSize: 13 }}>{username}@fmails.in</Text>
                    </View>
                    {handleState.checking ? <ActivityIndicator size="small" color={colors.muted} /> :
                      handleState.available === true ? <Icon name="check-circle" size={18} color={colors.success} /> :
                      handleState.available === false ? <Icon name="close-circle" size={18} color={colors.error} /> : null}
                  </View>
                ) : null}
                {handleState.available === false ? <Text style={{ color: colors.error, fontSize: 12, marginTop: 4 }} testID="handle-taken">{handleState.reason}</Text> : null}
                {handleState.available === true ? <Text style={{ color: colors.success, fontSize: 12, marginTop: 4 }} testID="handle-available">Available!</Text> : null}
              </View>
              <Field icon="email-outline" placeholder="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" testID="signup-email" />
              <Field icon="lock-outline" placeholder="Password (min 6 chars)" value={password} onChangeText={setPassword} secureTextEntry testID="signup-password" />
            </View>

            {error ? <Text style={{ color: colors.error, marginTop: 12 }} testID="signup-error">{error}</Text> : null}
            <Button title="Continue" onPress={requestCode} loading={loading} testID="signup-continue" style={{ marginTop: 24 }} disabled={handleState.available === false} />

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
            <Button title="Create my Fmail" onPress={onCreate} loading={loading} testID="signup-submit" style={{ marginTop: 20 }} />
            <Pressable onPress={resend} disabled={cooldown > 0} style={{ marginTop: 18, alignItems: "center" }} testID="resend-otp">
              <T color={cooldown > 0 ? colors.muted : colors.brandPrimary}>{cooldown > 0 ? `Resend code in ${cooldown}s` : "Resend code"}</T>
            </Pressable>
          </>
        )}
      </KeyboardAwareScrollView>
    </View>
  );
}
