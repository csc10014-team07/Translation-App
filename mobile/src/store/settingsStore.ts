import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import {
  DEFAULT_TARGET_CODE,
  TargetLanguageCode,
} from '../constants/languages';

export type ThemeMode = 'light' | 'dark' | 'system';

interface SettingsState {
  // ── State ──
  defaultTargetLang: TargetLanguageCode;
  themeMode: ThemeMode;
  /** Đánh dấu đã đọc xong cấu hình từ bộ nhớ (true sau onRehydrateStorage). */
  hasHydrated: boolean;

  // ── Actions ──
  setDefaultTargetLang: (code: TargetLanguageCode) => void;
  setThemeMode: (mode: ThemeMode) => void;
}

/**
 * Store cài đặt người dùng, lưu bền vào AsyncStorage.
 * Chỉ persist 2 trường cấu hình (không persist hasHydrated).
 */
export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      defaultTargetLang: DEFAULT_TARGET_CODE,
      themeMode: 'system',
      hasHydrated: false,

      setDefaultTargetLang: (code) => set({ defaultTargetLang: code }),
      setThemeMode: (mode) => set({ themeMode: mode }),
    }),
    {
      name: 'translation-settings',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        defaultTargetLang: state.defaultTargetLang,
        themeMode: state.themeMode,
      }),
      onRehydrateStorage: () => () => {
        // Chạy sau khi đọc xong từ bộ nhớ (kể cả khi lỗi → dùng mặc định).
        useSettingsStore.setState({ hasHydrated: true });
      },
    },
  ),
);

/** Cờ truy cập nhanh (không cần hook) để kiểm tra đã hydrate chưa. */
export function isSettingsHydrated(): boolean {
  return useSettingsStore.getState().hasHydrated;
}
