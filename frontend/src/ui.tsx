import React from "react";
import {
  View, Text, Pressable, ActivityIndicator, ScrollView, TextInput,
  Modal, StyleProp, ViewStyle, TextStyle, Platform, Image, KeyboardAvoidingView, Keyboard,
} from "react-native";
import MDIcon from "@react-native-vector-icons/material-design-icons";
import { useTheme, makeStyles, spacing, radius, ThemeColors } from "@/src/theme";

// ---------------- Icon ----------------
export function Icon({ name, size = 22, color }: { name: any; size?: number; color?: string }) {
  const { colors } = useTheme();
  return <MDIcon name={name} size={size} color={color ?? colors.onSurface} />;
}

// ---------------- Text helpers ----------------
export function T({ children, style, size = 15, weight = "400", color, numberOfLines }:
  { children: React.ReactNode; style?: StyleProp<TextStyle>; size?: number; weight?: TextStyle["fontWeight"]; color?: string; numberOfLines?: number }) {
  const { colors } = useTheme();
  return (
    <Text numberOfLines={numberOfLines} style={[{ color: color ?? colors.onSurface, fontSize: size, fontWeight: weight, letterSpacing: -0.2 }, style]}>
      {children}
    </Text>
  );
}

// ---------------- Card ----------------
export function Card({ children, style, onPress, testID }:
  { children: React.ReactNode; style?: StyleProp<ViewStyle>; onPress?: () => void; testID?: string }) {
  const s = useCardStyles();
  const Comp: any = onPress ? Pressable : View;
  return (
    <Comp testID={testID} onPress={onPress} style={({ pressed }: any) => [s.card, onPress && pressed && s.pressed, style]}>
      {children}
    </Comp>
  );
}
const useCardStyles = makeStyles((c) => ({
  card: { backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.lg, borderWidth: 1, borderColor: c.border },
  pressed: { opacity: 0.7 },
}));

// ---------------- Button ----------------
export function Button({ title, onPress, variant = "primary", icon, loading, disabled, testID, style, small }:
  { title: string; onPress?: () => void; variant?: "primary" | "secondary" | "ghost" | "danger"; icon?: any; loading?: boolean; disabled?: boolean; testID?: string; style?: StyleProp<ViewStyle>; small?: boolean }) {
  const { colors } = useTheme();
  const bg = variant === "primary" ? colors.brandPrimary : variant === "danger" ? colors.error : variant === "secondary" ? colors.brandTertiary : "transparent";
  const fg = variant === "primary" || variant === "danger" ? colors.onBrandPrimary : variant === "secondary" ? colors.onBrandTertiary : colors.brandPrimary;
  return (
    <Pressable testID={testID} disabled={disabled || loading} onPress={onPress}
      style={({ pressed }) => [{
        backgroundColor: bg, borderRadius: radius.pill, paddingVertical: small ? 9 : 14, paddingHorizontal: small ? 16 : 20,
        flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8,
        opacity: disabled ? 0.5 : pressed ? 0.85 : 1, minHeight: small ? 38 : 50,
      }, style]}>
      {loading ? <ActivityIndicator color={fg} /> : (
        <>
          {icon ? <MDIcon name={icon} size={small ? 16 : 19} color={fg} /> : null}
          <Text style={{ color: fg, fontWeight: "700", fontSize: small ? 13 : 15 }}>{title}</Text>
        </>
      )}
    </Pressable>
  );
}

// ---------------- Chip ----------------
export function Chip({ label, active, onPress, testID, icon }:
  { label: string; active?: boolean; onPress?: () => void; testID?: string; icon?: any }) {
  const { colors } = useTheme();
  return (
    <Pressable testID={testID} onPress={onPress}
      style={{
        height: 36, flexShrink: 0, paddingHorizontal: 14, borderRadius: radius.pill,
        flexDirection: "row", alignItems: "center", gap: 6,
        backgroundColor: active ? colors.brandPrimary : colors.surfaceSecondary,
        borderWidth: 1, borderColor: active ? colors.brandPrimary : colors.border,
      }}>
      {icon ? <MDIcon name={icon} size={15} color={active ? colors.onBrandPrimary : colors.muted} /> : null}
      <Text style={{ color: active ? colors.onBrandPrimary : colors.onSurfaceTertiary, fontWeight: "600", fontSize: 13 }}>{label}</Text>
    </Pressable>
  );
}

// ---------------- Badge ----------------
const LABEL_COLORS: Record<string, string> = {
  Urgent: "#D64545", "Action Required": "#FF5E00", "Waiting for Reply": "#C98A00",
  Important: "#FF6600", FYI: "#757575", Promotional: "#9A6BFF", Newsletter: "#2F6FED",
  Finance: "#1E9E5A", Social: "#2F6FED", Personal: "#1E9E5A", Work: "#FF5E00",
};
export function Badge({ label, color, tone }: { label: string; color?: string; tone?: "solid" | "soft" }) {
  const c = color ?? LABEL_COLORS[label] ?? "#757575";
  const soft = tone !== "solid";
  return (
    <View style={{ backgroundColor: soft ? c + "22" : c, paddingHorizontal: 9, paddingVertical: 4, borderRadius: radius.sm, alignSelf: "flex-start" }}>
      <Text style={{ color: soft ? c : "#fff", fontSize: 11, fontWeight: "700" }}>{label}</Text>
    </View>
  );
}

// ---------------- Avatar ----------------
export function Avatar({ name, size = 42, uri }: { name: string; size?: number; uri?: string | null }) {
  const { colors } = useTheme();
  const initials = (name || "?").split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  const palette = ["#FF5E00", "#2F6FED", "#1E9E5A", "#C98A00", "#9A6BFF", "#D64545"];
  const bg = palette[(name?.charCodeAt(0) || 0) % palette.length];
  return (
    <View style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: bg, alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
      {uri ? <Image source={{ uri }} style={{ width: size, height: size }} resizeMode="cover" /> : <Text style={{ color: "#fff", fontWeight: "700", fontSize: size * 0.38 }}>{initials}</Text>}
    </View>
  );
}

// ---------------- States ----------------
export function Loading({ label }: { label?: string }) {
  const { colors } = useTheme();
  return (
    <View style={{ padding: spacing.xxl, alignItems: "center", justifyContent: "center", flex: 1 }}>
      <ActivityIndicator color={colors.brandPrimary} size="large" />
      {label ? <Text style={{ color: colors.muted, marginTop: 12 }}>{label}</Text> : null}
    </View>
  );
}
export function ErrorState({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  const { colors } = useTheme();
  return (
    <View style={{ padding: spacing.xxl, alignItems: "center", gap: 14 }} testID="error-state">
      <Icon name="cloud-off-outline" size={40} color={colors.muted} />
      <Text style={{ color: colors.onSurface, textAlign: "center", fontSize: 15 }}>{message || "Couldn't load this. Please try again."}</Text>
      {onRetry ? <Button title="Retry" variant="secondary" small onPress={onRetry} icon="refresh" testID="retry-button" /> : null}
    </View>
  );
}
export function Empty({ icon = "inbox-outline", title, subtitle }: { icon?: any; title: string; subtitle?: string }) {
  const { colors } = useTheme();
  return (
    <View style={{ padding: spacing.xxl, alignItems: "center", gap: 8 }} testID="empty-state">
      <View style={{ width: 68, height: 68, borderRadius: 34, backgroundColor: colors.brandTertiary, alignItems: "center", justifyContent: "center" }}>
        <Icon name={icon} size={32} color={colors.brandPrimary} />
      </View>
      <Text style={{ color: colors.onSurface, fontSize: 17, fontWeight: "700", marginTop: 6 }}>{title}</Text>
      {subtitle ? <Text style={{ color: colors.muted, textAlign: "center", fontSize: 14 }}>{subtitle}</Text> : null}
    </View>
  );
}

// ---------------- Input ----------------
export function Field({ value, onChangeText, placeholder, secureTextEntry, testID, multiline, keyboardType, autoCapitalize, icon, style }:
  any) {
  const { colors } = useTheme();
  return (
    <View style={[{ flexDirection: "row", alignItems: multiline ? "flex-start" : "center", gap: 10, backgroundColor: colors.surfaceTertiary, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: multiline ? 12 : 0, minHeight: 52, borderWidth: 1, borderColor: colors.border }, style]}>
      {icon ? <View style={{ paddingTop: multiline ? 2 : 0 }}><Icon name={icon} size={18} color={colors.muted} /></View> : null}
      <TextInput
        testID={testID}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.muted}
        secureTextEntry={secureTextEntry}
        multiline={multiline}
        keyboardType={keyboardType}
        autoCapitalize={autoCapitalize}
        style={{ flex: 1, color: colors.onSurface, fontSize: 15, paddingVertical: multiline ? 0 : 14, minHeight: multiline ? 90 : undefined, textAlignVertical: multiline ? "top" : "center" }}
      />
    </View>
  );
}

// ---------------- Sheet (modal) ----------------
export function Sheet({ visible, onClose, children, title, testID }:
  { visible: boolean; onClose: () => void; children: React.ReactNode; title?: string; testID?: string }) {
  const { colors } = useTheme();
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable onPress={onClose} style={{ flex: 1, backgroundColor: "#00000066", justifyContent: "flex-end" }}>
        <Pressable testID={testID} onPress={(e) => e.stopPropagation()} style={{ backgroundColor: colors.surface, borderTopLeftRadius: radius.xl, borderTopRightRadius: radius.xl, maxHeight: "88%", paddingBottom: 34 }}>
          <View style={{ alignItems: "center", paddingTop: 10 }}>
            <View style={{ width: 40, height: 4, borderRadius: 2, backgroundColor: colors.borderStrong }} />
          </View>
          {title ? (
            <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: spacing.lg, paddingVertical: spacing.md }}>
              <Text style={{ color: colors.onSurface, fontSize: 19, fontWeight: "800" }}>{title}</Text>
              <Pressable onPress={onClose} testID="sheet-close"><Icon name="close" size={24} color={colors.muted} /></Pressable>
            </View>
          ) : null}
          <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"}>
            <ScrollView style={{ paddingHorizontal: spacing.lg }} contentContainerStyle={{ paddingBottom: 20 }} keyboardShouldPersistTaps="handled" keyboardDismissMode="interactive">
              {children}
            </ScrollView>
          </KeyboardAvoidingView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

export { spacing, radius };
