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

/**
 * @deprecated Dùng `LanguageCode` (suy ra từ `LANGUAGE_CATALOG`) cho code mới.
 * Giữ lại để không phá vỡ các import cũ.
 */
export type OldLanguageCode = (typeof LANGUAGES)[number]['code'];

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
// Catalog ngôn ngữ (nguồn dữ liệu đã chốt)
// ──────────────────────────────────────────────
//
// Danh sách này bám sát `docs/language-support.md`:
//   - 11 ngôn ngữ backend DỊCH được (translation_adapter.py → LANGUAGE_NAMES):
//     vi, en, ja, zh, ko, fr, de, es, pt, ru, it.
//   - KHÔNG đưa 'nl' (Hà Lan): backend không dịch được.
//   - Code phải là ĐÚNG chuỗi backend nhận. Backend chấp nhận cả mã ISO
//     ('zh') lẫn tên tiếng Anh ('Chinese'), nhưng ta luôn dùng mã ISO.
//   - 'zh' là tiếng Trung Giản thể (KHÔNG phải 'zh-CN').

export interface Language {
  /** Mã ngôn ngữ backend nhận (ISO 639-1), ví dụ 'vi', 'en', 'zh'. */
  code: string;
  /** Nhãn đầy đủ hiển thị trong danh sách, ví dụ 'Tiếng Việt'. */
  label: string;
  /** Nhãn ngắn hiển thị trên thẻ/nút, ví dụ '中文'. */
  shortLabel: string;
  /** Có dùng làm ngôn ngữ NGUỒN để dịch văn bản được không. */
  canBeSource: boolean;
  /** Có dùng làm ngôn ngữ ĐÍCH được không. */
  canBeTarget: boolean;
  /** Có nhập bằng GIỌNG NÓI được không (ASR chỉ hỗ trợ tiếng Việt). */
  supportsVoiceInput: boolean;
  /** Có QUÉT CHỮ được không (OCR chỉ nhận diện chắc vi/en/ja/zh). */
  supportsOcr: boolean;
  /** Có ĐỌC TO được không (Edge-TTS). */
  supportsTts: boolean;
}

/** Thứ tự khai báo catalog (nhóm theo mức hỗ trợ, không phải thứ tự hiển thị). */
export const LANGUAGE_CATALOG = [
  {
    code: 'vi',
    label: 'Tiếng Việt',
    shortLabel: 'Tiếng Việt',
    canBeSource: true,
    canBeTarget: true,
    supportsVoiceInput: true,
    supportsOcr: true,
    supportsTts: true,
  },
  {
    code: 'en',
    label: 'English',
    shortLabel: 'English',
    canBeSource: true,
    canBeTarget: true,
    supportsVoiceInput: false,
    supportsOcr: true,
    supportsTts: true,
  },
  {
    code: 'zh',
    label: '中文 (Mandarin)',
    shortLabel: '中文',
    canBeSource: true,
    canBeTarget: true,
    supportsVoiceInput: false,
    supportsOcr: true,
    supportsTts: true,
  },
  {
    code: 'ja',
    label: '日本語 (Japanese)',
    shortLabel: '日本語',
    canBeSource: true,
    canBeTarget: true,
    supportsVoiceInput: false,
    supportsOcr: true,
    supportsTts: true,
  },
  {
    code: 'ko',
    label: '한국어 (Korean)',
    shortLabel: '한국어',
    canBeSource: true,
    canBeTarget: true,
    supportsVoiceInput: false,
    supportsOcr: false,
    supportsTts: true,
  },
  {
    code: 'fr',
    label: 'Français (French)',
    shortLabel: 'Français',
    canBeSource: true,
    canBeTarget: true,
    supportsVoiceInput: false,
    supportsOcr: false,
    supportsTts: true,
  },
  {
    code: 'de',
    label: 'Deutsch (German)',
    shortLabel: 'Deutsch',
    canBeSource: true,
    canBeTarget: true,
    supportsVoiceInput: false,
    supportsOcr: false,
    supportsTts: true,
  },
  {
    code: 'es',
    label: 'Español (Spanish)',
    shortLabel: 'Español',
    canBeSource: true,
    canBeTarget: true,
    supportsVoiceInput: false,
    supportsOcr: false,
    supportsTts: true,
  },
  {
    code: 'pt',
    label: 'Português (Portuguese)',
    shortLabel: 'Português',
    canBeSource: true,
    canBeTarget: true,
    supportsVoiceInput: false,
    supportsOcr: false,
    supportsTts: true,
  },
  {
    code: 'ru',
    label: 'Русский (Russian)',
    shortLabel: 'Русский',
    canBeSource: true,
    canBeTarget: true,
    supportsVoiceInput: false,
    supportsOcr: false,
    supportsTts: true,
  },
  {
    code: 'it',
    label: 'Italiano (Italian)',
    shortLabel: 'Italiano',
    canBeSource: true,
    canBeTarget: true,
    supportsVoiceInput: false,
    supportsOcr: false,
    supportsTts: true,
  },
] as const satisfies readonly Language[];

/** Mã ngôn ngữ được backend hỗ trợ, suy ra từ catalog. */
export type LanguageCode = (typeof LANGUAGE_CATALOG)[number]['code'];

/** Mã ngôn ngữ nguồn mặc định (Tiếng Việt). */
export const DEFAULT_SOURCE_CODE: LanguageCode = 'vi';

/** Mã ngôn ngữ đích mặc định (English). */
export const DEFAULT_TARGET_CODE: LanguageCode = 'en';

// ──────────────────────────────────────────────
// Danh sách nguồn / đích (đã sắp theo thứ tự hiển thị)
// ──────────────────────────────────────────────

/**
 * Ngôn ngữ NGUỒN ("Dịch từ") theo thứ tự hiển thị:
 * Tiếng Việt → English → 中文 → 日本語 → 한국어 → Français → Deutsch → Español
 * → Português → Русский → Italiano.
 */
export const SOURCE_LANGUAGES: Language[] = [
  getCatalogLanguage('vi'),
  getCatalogLanguage('en'),
  getCatalogLanguage('zh'),
  getCatalogLanguage('ja'),
  getCatalogLanguage('ko'),
  getCatalogLanguage('fr'),
  getCatalogLanguage('de'),
  getCatalogLanguage('es'),
  getCatalogLanguage('pt'),
  getCatalogLanguage('ru'),
  getCatalogLanguage('it'),
].filter((l): l is Language => l !== undefined);

/**
 * Ngôn ngữ ĐÍCH ("Dịch sang") theo thứ tự cũ + Tiếng Việt ở cuối:
 * English → 中文 → 日本語 → 한국어 → Français → Deutsch → Español → Português
 * → Русский → Italiano → Tiếng Việt.
 */
export const TARGET_LANGUAGES: Language[] = [
  getCatalogLanguage('en'),
  getCatalogLanguage('zh'),
  getCatalogLanguage('ja'),
  getCatalogLanguage('ko'),
  getCatalogLanguage('fr'),
  getCatalogLanguage('de'),
  getCatalogLanguage('es'),
  getCatalogLanguage('pt'),
  getCatalogLanguage('ru'),
  getCatalogLanguage('it'),
  getCatalogLanguage('vi'),
].filter((l): l is Language => l !== undefined);

/** Lấy một mục trong catalog theo mã (không tính thời gian chạy). */
function getCatalogLanguage(code: string): Language | undefined {
  return LANGUAGE_CATALOG.find((l) => l.code === code);
}

// ──────────────────────────────────────────────
// Hàm tra cứu
// ──────────────────────────────────────────────

/** Trả về mục catalog của một mã (hoặc `undefined` nếu không hỗ trợ). */
export function getLanguage(code: string): Language | undefined {
  return getCatalogLanguage(code);
}

/** Nhãn ngắn hiển thị ở ô "Dịch từ"; không có thì trả lại chính mã. */
export function getSourceLabel(code: string): string {
  return getLanguage(code)?.shortLabel ?? code;
}

/** Nhãn đầy đủ hiển thị trong danh sách "Dịch từ"; không có thì trả mã. */
export function getSourceFullLabel(code: string): string {
  return getLanguage(code)?.label ?? code;
}

/** Nhãn ngắn hiển thị trên thẻ "Dịch sang"; không có thì trả lại chính mã. */
export function getTargetLabel(code: string): string {
  return getLanguage(code)?.shortLabel ?? code;
}

/** Nhãn đầy đủ hiển thị trong danh sách "Dịch sang"; không có thì trả mã. */
export function getTargetFullLabel(code: string): string {
  return getLanguage(code)?.label ?? code;
}

/** Mã này có nhập bằng giọng nói được không (ASR chỉ tiếng Việt). */
export function supportsVoiceInput(code: string): boolean {
  return getLanguage(code)?.supportsVoiceInput ?? false;
}

/** Mã này có quét chữ được không (OCR chắc chắn: vi/en/ja/zh). */
export function supportsOcr(code: string): boolean {
  return getLanguage(code)?.supportsOcr ?? false;
}

/** Mã này có đọc to được không (Edge-TTS). */
export function supportsTts(code: string): boolean {
  return getLanguage(code)?.supportsTts ?? false;
}

// ──────────────────────────────────────────────
// Tương thích ngược
// ──────────────────────────────────────────────

/**
 * @deprecated Alias của `LanguageCode`. Dùng `LanguageCode` cho code mới.
 */
export type TargetLanguageCode = LanguageCode;
