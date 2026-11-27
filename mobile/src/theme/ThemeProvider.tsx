import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  ReactNode,
} from 'react';
import { useColorScheme, StyleSheet, ViewStyle, TextStyle, ImageStyle } from 'react-native';
import { lightColors, darkColors, ThemeColors } from './colors';
import { useSettingsStore, ThemeMode } from '../store/settingsStore';

type NamedStyles<T> = { [P in keyof T]: ViewStyle | TextStyle | ImageStyle };

export type Mode = 'light' | 'dark';

interface ThemeContextType {
  colors: ThemeColors;
  mode: Mode;
  toggleMode: () => void;
  setMode: (mode: Mode) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const systemScheme = useColorScheme();
  const themeMode = useSettingsStore((s) => s.themeMode);
  const setThemeMode = useSettingsStore((s) => s.setThemeMode);

  // Giải nghĩa 'system' → mode hệ thống hiện tại, 'light'/'dark' → dùng trực tiếp.
  const resolvedMode: Mode = useMemo(() => {
    if (themeMode === 'system') {
      return systemScheme ?? 'light';
    }
    return themeMode;
  }, [themeMode, systemScheme]);

  const colors = useMemo(
    () => (resolvedMode === 'dark' ? darkColors : lightColors),
    [resolvedMode],
  );

  const setMode = useCallback(
    (next: Mode) => {
      setThemeMode(next);
    },
    [setThemeMode],
  );

  const toggleMode = useCallback(() => {
    // Từ 'system' → đảo so với giá trị hệ thống hiện tại; 'light'↔'dark'.
    const current: Mode =
      themeMode === 'system' ? (systemScheme ?? 'light') : themeMode;
    const next: ThemeMode = current === 'light' ? 'dark' : 'light';
    setThemeMode(next);
  }, [themeMode, systemScheme, setThemeMode]);

  const value = useMemo(
    () => ({ colors, mode: resolvedMode, toggleMode, setMode }),
    [colors, resolvedMode, toggleMode, setMode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextType {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return ctx;
}

/**
 * Tạo StyleSheet động theo theme, memo theo colors.
 * Ví dụ:
 *   const styles = useThemedStyles((colors) => ({
 *     container: { backgroundColor: colors.background },
 *   }));
 */
export function useThemedStyles<T extends NamedStyles<T>>(
  makeStyles: (colors: ThemeColors) => T
): T {
  const { colors } = useTheme();
  return useMemo(
    () => StyleSheet.create(makeStyles(colors)) as unknown as T,
    [colors],
  );
}
