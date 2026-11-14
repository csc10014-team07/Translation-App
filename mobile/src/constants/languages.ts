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

export const TARGET_LANGUAGES = [
  ...LANGUAGES.filter((language) => language.code !== 'vi'),
  ...LANGUAGES.filter((language) => language.code === 'vi'),
];

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
