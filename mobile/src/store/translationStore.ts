import { create } from 'zustand';
import {
  transcribeAudio as apiTranscribeAudio,
  ocrImage as apiOcrImage,
  translateText as apiTranslateText,
  synthesizeSpeech as apiSynthesizeSpeech,
  saveBase64Audio,
} from '../services/api';

// ──────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────

type InputMode = 'text' | 'voice' | 'image';

export interface TranslationState {
  // ── Input ──
  inputMode: InputMode;
  vietnameseText: string;
  context: string;
  targetLanguage: string;

  // ── Output ──
  translatedText: string;
  sourceLanguage: string;

  // ── Voice cloning ──
  referenceAudioUri: string | null;
  referenceText: string;
  synthesizedAudioUri: string | null;

  // ── UI state ──
  isTranscribing: boolean;
  isOcrProcessing: boolean;
  isTranslating: boolean;
  isSynthesizing: boolean;
  error: string | null;

  // ── Actions ──
  setInputMode: (mode: InputMode) => void;
  setVietnameseText: (text: string) => void;
  setContext: (context: string) => void;
  setTargetLanguage: (lang: string) => void;
  transcribeAudio: (audioUri: string) => Promise<void>;
  processImage: (imageUri: string) => Promise<void>;
  translate: () => Promise<void>;
  setReferenceAudio: (uri: string) => void;
  setReferenceText: (text: string) => void;
  synthesize: () => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

// ──────────────────────────────────────────────
// Default / initial state values
// ──────────────────────────────────────────────

const initialState = {
  inputMode: 'text' as InputMode,
  vietnameseText: '',
  context: '',
  targetLanguage: 'en',
  translatedText: '',
  sourceLanguage: '',
  referenceAudioUri: null as string | null,
  referenceText: '',
  synthesizedAudioUri: null as string | null,
  isTranscribing: false,
  isOcrProcessing: false,
  isTranslating: false,
  isSynthesizing: false,
  error: null as string | null,
};

// ──────────────────────────────────────────────
// Store
// ──────────────────────────────────────────────

export const useTranslationStore = create<TranslationState>((set, get) => ({
  ...initialState,

  setInputMode: (mode) => set({ inputMode: mode }),

  setVietnameseText: (text) => set({ vietnameseText: text }),

  setContext: (context) => set({ context }),

  setTargetLanguage: (lang) => set({ targetLanguage: lang }),

  transcribeAudio: async (audioUri: string) => {
    set({ isTranscribing: true, error: null });
    try {
      const result = await apiTranscribeAudio(audioUri);
      set({ vietnameseText: result.text });
    } catch (e: unknown) {
      set({ error: extractErrorMessage(e, 'Failed to transcribe audio.') });
    } finally {
      set({ isTranscribing: false });
    }
  },

  processImage: async (imageUri: string) => {
    set({ isOcrProcessing: true, error: null });
    try {
      const result = await apiOcrImage(imageUri);
      set({ vietnameseText: result.vietnamese_text });
    } catch (e: unknown) {
      set({ error: extractErrorMessage(e, 'Failed to process image.') });
    } finally {
      set({ isOcrProcessing: false });
    }
  },

  translate: async () => {
    const { vietnameseText, targetLanguage, context } = get();
    if (!vietnameseText.trim()) {
      set({ error: 'Please enter or record Vietnamese text first.' });
      return;
    }
    set({ isTranslating: true, error: null, translatedText: '' });
    try {
      const result = await apiTranslateText(
        vietnameseText,
        targetLanguage,
        context || undefined,
      );
      set({
        translatedText: result.translated_text,
        sourceLanguage: result.source_language,
      });
    } catch (e: unknown) {
      set({ error: extractErrorMessage(e, 'Translation failed.') });
    } finally {
      set({ isTranslating: false });
    }
  },

  setReferenceAudio: (uri: string) => set({ referenceAudioUri: uri }),

  setReferenceText: (text: string) => set({ referenceText: text }),

  synthesize: async () => {
    const {
      translatedText,
      targetLanguage,
      referenceAudioUri,
      referenceText,
    } = get();
    if (!translatedText.trim()) {
      set({ error: 'Please translate some text first.' });
      return;
    }
    if (targetLanguage === 'vi') {
      set({ error: 'TTS is not available for Vietnamese.' });
      return;
    }
    set({ isSynthesizing: true, error: null, synthesizedAudioUri: null });
    try {
      const result = await apiSynthesizeSpeech(
        translatedText,
        targetLanguage,
        referenceAudioUri ?? undefined,
        referenceText || undefined,
      );
      const localUri = await saveBase64Audio(result.audio_base64, result.format);
      set({ synthesizedAudioUri: localUri });
    } catch (e: unknown) {
      set({ error: extractErrorMessage(e, 'Speech synthesis failed.') });
    } finally {
      set({ isSynthesizing: false });
    }
  },

  clearError: () => set({ error: null }),

  reset: () => set({ ...initialState }),
}));

// ──────────────────────────────────────────────
// Utility
// ──────────────────────────────────────────────

function extractErrorMessage(e: unknown, fallback: string): string {
  if (typeof e === 'object' && e !== null) {
    const err = e as Record<string, unknown>;
    if (
      typeof err['response'] === 'object' &&
      err['response'] !== null
    ) {
      const resp = err['response'] as Record<string, unknown>;
      if (
        typeof resp['data'] === 'object' &&
        resp['data'] !== null
      ) {
        const data = resp['data'] as Record<string, unknown>;
        if (typeof data['detail'] === 'string') return data['detail'];
        if (typeof data['message'] === 'string') return data['message'];
      }
    }
    if (typeof err['message'] === 'string') return err['message'];
  }
  return fallback;
}
