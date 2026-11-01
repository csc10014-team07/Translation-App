export const TARGET_LANGUAGES = [
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
  { code: 'vi', name: 'Vietnamese' }, // translation only, no TTS
] as const;

export type LanguageCode = (typeof TARGET_LANGUAGES)[number]['code'];

export const TTS_SUPPORTED_LANGUAGES = TARGET_LANGUAGES.filter(
  (l) => l.code !== 'vi',
);
