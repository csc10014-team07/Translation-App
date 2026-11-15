import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import {
  DEFAULT_SOURCE_CODE,
  getLanguage,
  LanguageCode,
} from '../constants/languages';

export type ThemeMode = 'light' | 'dark' | 'system';

interface SettingsState {
  // ── State ──
  /** Ngôn ngữ NGUỒN mặc định ("Dịch từ"), lưu bền và áp khi mở app. */
  defaultSourceLang: LanguageCode;
  themeMode: ThemeMode;
  /** Đánh dấu đã đọc xong cấu hình từ bộ nhớ (true sau onRehydrateStorage). */
  hasHydrated: boolean;

  // ── Actions ──
  setDefaultSourceLang: (code: LanguageCode) => void;
  setThemeMode: (mode: ThemeMode) => void;
}

/** Phần thực sự được ghi xuống bộ nhớ. */
type PersistedSettings = {
  defaultSourceLang: LanguageCode;
  themeMode: ThemeMode;
};

/** Tăng khi đổi cấu trúc dữ liệu lưu (kích hoạt migrate). */
const PERSIST_VERSION = 1;

/**
 * Store cài đặt người dùng, lưu bền vào AsyncStorage.
 * Chỉ persist `defaultSourceLang` + `themeMode` (không persist hasHydrated).
 */
export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      defaultSourceLang: DEFAULT_SOURCE_CODE,
      themeMode: 'system',
      hasHydrated: false,

      setDefaultSourceLang: (code) => {
        // Bỏ qua mã không có trong catalog.
        if (!getLanguage(code)) return;
        set({ defaultSourceLang: code });
      },
      setThemeMode: (mode) => set({ themeMode: mode }),
    }),
    {
      name: 'translation-settings',
      version: PERSIST_VERSION,
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state): PersistedSettings => ({
        defaultSourceLang: state.defaultSourceLang,
        themeMode: state.themeMode,
      }),
      /**
       * Dữ liệu cũ (version 0) có `defaultTargetLang` → BỎ QUA. Chỉ dựng lại
       * `defaultSourceLang` (mã hợp lệ, mặc định 'vi') và `themeMode`.
       */
      migrate: (persistedState): PersistedSettings => {
        const old = (persistedState ?? {}) as {
          defaultSourceLang?: unknown;
          themeMode?: unknown;
        };
        const themeMode: ThemeMode =
          old.themeMode === 'light' ||
          old.themeMode === 'dark' ||
          old.themeMode === 'system'
            ? old.themeMode
            : 'system';
        const source =
          typeof old.defaultSourceLang === 'string' &&
          getLanguage(old.defaultSourceLang)
            ? (old.defaultSourceLang as LanguageCode)
            : DEFAULT_SOURCE_CODE;
        return { defaultSourceLang: source, themeMode };
      },
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
