// Fmail design tokens — premium, minimal, warm-orange brand.
// Light + Dark. Keys match design_guidelines color block. Use makeStyles()/useTheme().

import { useMemo } from "react";
import { Appearance, StyleSheet, useColorScheme } from "react-native";

export type ColorScheme = "light" | "dark";

const light = {
  surface: "#F8F9FA",
  onSurface: "#1C1C1E",
  surfaceSecondary: "#FFFFFF",
  onSurfaceSecondary: "#1C1C1E",
  surfaceTertiary: "#EEF1F4",
  onSurfaceTertiary: "#4A4A4E",
  surfaceInverse: "#1C1C1E",
  onSurfaceInverse: "#FFFFFF",
  muted: "#757575",

  brand: "#FF5500",
  onBrand: "#FFFFFF",
  brandPrimary: "#FF5500",
  onBrandPrimary: "#FFFFFF",
  brandSecondary: "#FF6A1A",
  onBrandSecondary: "#FFFFFF",
  brandTertiary: "#FFEFE6",
  onBrandTertiary: "#C24000",

  success: "#1E9E5A",
  onSuccess: "#FFFFFF",
  warning: "#C98A00",
  onWarning: "#FFFFFF",
  error: "#D64545",
  onError: "#FFFFFF",
  info: "#2F6FED",
  onInfo: "#FFFFFF",

  border: "#E7E9EC",
  borderStrong: "#D4D7DC",
  divider: "#EDEFF2",
};

const dark: typeof light = {
  surface: "#0E0F11",
  onSurface: "#F5F6F8",
  surfaceSecondary: "#17181B",
  onSurfaceSecondary: "#F5F6F8",
  surfaceTertiary: "#232529",
  onSurfaceTertiary: "#C7C9CE",
  surfaceInverse: "#F5F6F8",
  onSurfaceInverse: "#1C1C1E",
  muted: "#9A9CA2",

  brand: "#FF6A1A",
  onBrand: "#FFFFFF",
  brandPrimary: "#FF7A2E",
  onBrandPrimary: "#FFFFFF",
  brandSecondary: "#FF8A44",
  onBrandSecondary: "#FFFFFF",
  brandTertiary: "#2A1810",
  onBrandTertiary: "#FF9A57",

  success: "#3DBB74",
  onSuccess: "#08130C",
  warning: "#E0A93B",
  onWarning: "#1C1405",
  error: "#F16A6A",
  onError: "#1C0808",
  info: "#5B8DF0",
  onInfo: "#07101F",

  border: "#2A2C31",
  borderStrong: "#3A3D43",
  divider: "#232529",
};

export type ThemeColors = typeof light;

export const defaultScheme = "light" satisfies ColorScheme;
export const themes: { light: ThemeColors; dark?: ThemeColors } = { light, dark };

export function setColorScheme(scheme: ColorScheme | null) {
  Appearance.setColorScheme?.(scheme ?? "unspecified");
}

setColorScheme?.(themes.dark ? null : defaultScheme);

export function useTheme(): { scheme: ColorScheme; colors: ThemeColors } {
  const system = useColorScheme();
  const scheme: ColorScheme = system && themes[system] ? system : defaultScheme;
  return { scheme, colors: themes[scheme] ?? themes.light };
}

export function makeStyles<T extends StyleSheet.NamedStyles<T> | StyleSheet.NamedStyles<any>>(
  factory: (colors: ThemeColors) => T & StyleSheet.NamedStyles<any>,
): () => T {
  return function useStyles(): T {
    const { colors } = useTheme();
    return useMemo(() => StyleSheet.create(factory(colors)), [colors]);
  };
}

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };
export const radius = { sm: 10, md: 16, lg: 20, xl: 24, pill: 999 };
