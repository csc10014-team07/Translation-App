// ──────────────────────────────────────────────
// Phần giữ nguyên từ bản cũ (không xoá, không đổi thứ tự)
// ──────────────────────────────────────────────

export const LANGUAGES = [
  { code: 'vi', name: 'Vietnamese' },
  { code: 'en', name: 'English' },
  { code: 'zh', name: 'Chinese (Simplified)' },
  { code: 'ja', name: 'Japanese' },
  { code: 'ko', name: 'Korean' },
  { code: 'fr', name: 'French' },
  { code: 'de', name: 'German' },
  { code: 'es', name: 'Spanish' },
  { code: 'pt', name: 'Portuguese' },
  { code: 'ru', name: 'Russian' },
  { code: 'it', name: 'Italian' },
] as const;

export type LanguageCode = (typeof LANGUAGES)[number]['code'];

/** Languages supported by the bundled speech-to-text model (PhoASR). */
export const STT_LANGUAGES = LANGUAGES.filter((l) => l.code === 'vi');

export const TTS_SUPPORTED_LANGUAGES = LANGUAGES.filter(
  (l) => l.code !== 'vi',
);

export function supportsSpeechToText(code: string): boolean {
  return STT_LANGUAGES.some((language) => language.code === code);
}

export function getLanguageName(code: string): string {
  return LANGUAGES.find((language) => language.code === code)?.name ?? code;
}

// ──────────────────────────────────────────────
// Phần mới: ngôn ngữ nguồn + đích cho giao diện mới
// ──────────────────────────────────────────────

/** Ngôn ngữ nguồn cố định (nhận dạng giọng nói / ASR chỉ hỗ trợ tiếng Việt). */
export const SOURCE_LANGUAGE = { code: 'vi', label: 'Tiếng Việt' } as const;

/**
 * Danh sách ngôn ngữ ĐÍCH mà app hỗ trợ dịch sang.
 *
 * Mã `code` khớp chính xác với backend:
 *   - translation_adapter.py → LANGUAGE_NAMES (en, zh, ja, ko, fr, de, es, pt, ru, it)
 *   - tts_adapter.py → EDGE_VOICES_FEMALE / POCKET_TTS_LANG_MAP
 *
 * Ghi chú: backend dùng 'zh' (không phải 'zh-CN') cho tiếng Trung.
 * App cũ dùng mã giống → không cần đổi.
 */
export const TARGET_LANGUAGES = [
  { code: 'en', label: 'English', shortLabel: 'English' },
  { code: 'zh', label: '中文 (Mandarin)', shortLabel: '中文' },
  { code: 'ja', label: '日本語 (Japanese)', shortLabel: '日本語' },
  { code: 'ko', label: '한국어 (Korean)', shortLabel: '한국어' },
  { code: 'fr', label: 'Français (French)', shortLabel: 'Français' },
  { code: 'de', label: 'Deutsch (German)', shortLabel: 'Deutsch' },
  { code: 'es', label: 'Español (Spanish)', shortLabel: 'Español' },
  { code: 'pt', label: 'Português (Portuguese)', shortLabel: 'Português' },
  { code: 'ru', label: 'Русский (Russian)', shortLabel: 'Русский' },
  { code: 'it', label: 'Italiano (Italian)', shortLabel: 'Italiano' },
] as const;

/** Kiểu mã ngôn ngữ đích, suy ra từ TARGET_LANGUAGES. */
export type TargetLanguageCode = (typeof TARGET_LANGUAGES)[number]['code'];

/** Mã ngôn ngữ đích mặc định (English). */
export const DEFAULT_TARGET_CODE: TargetLanguageCode = 'en';

/** Trả về shortLabel (hiển thị trên thẻ "Dịch sang" ở màn chính). */
export function getTargetLabel(code: string): string {
  return TARGET_LANGUAGES.find((l) => l.code === code)?.shortLabel ?? code;
}

/** Trả về label đầy đủ (hiển thị trong danh sách chọn ngôn ngữ đích). */
export function getTargetFullLabel(code: string): string {
  return TARGET_LANGUAGES.find((l) => l.code === code)?.label ?? code;
}
