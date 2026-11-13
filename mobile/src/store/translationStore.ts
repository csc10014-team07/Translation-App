import { create } from 'zustand';
import {
  transcribeAudio as apiTranscribeAudio,
  ocrImage as apiOcrImage,
  translateText as apiTranslateText,
  synthesizeSpeech as apiSynthesizeSpeech,
  saveBase64Audio,
} from '../services/api';
import { StreamClient } from '../services/stream';
import {
  startLiveAudioCapture,
  stopLiveAudioCapture,
} from '../services/liveAudio';
import { supportsSpeechToText } from '../constants/languages';

// ──────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────

type InputMode = 'text' | 'voice' | 'image';

export interface TranslationState {
  // ── Input ──
  inputMode: InputMode;
  inputLanguage: string;
  vietnameseText: string;
  context: string;
  targetLanguage: string;

  // ── Output ──
  translatedText: string;
  sourceLanguage: string;

  // ── Voice cloning ──
  referenceAudioUri: string | null;
  synthesizedAudioUri: string | null;

  // ── UI state ──
  isTranscribing: boolean;
  isOcrProcessing: boolean;
  isTranslating: boolean;
  isSynthesizing: boolean;
  isStreaming: boolean;
  error: string | null;

  // ── Actions ──
  setInputMode: (mode: InputMode) => void;
  setInputLanguage: (lang: string) => void;
  setVietnameseText: (text: string) => void;
  setContext: (context: string) => void;
  setTargetLanguage: (lang: string) => void;
  transcribeAudio: (audioUri: string) => Promise<void>;
  processImage: (imageUri: string) => Promise<void>;
  translate: () => Promise<void>;
  setReferenceAudio: (uri: string) => void;
  synthesize: () => Promise<void>;
  startStreaming: (customUrl?: string) => Promise<void>;
  stopStreaming: () => void;
  sendStreamingAudio: (chunk: ArrayBuffer | Uint8Array) => void;
  clearError: () => void;
  reset: () => void;
}

// ──────────────────────────────────────────────
// Default / initial state values
// ──────────────────────────────────────────────

let activeStreamClient: StreamClient | null = null;
let streamSessionId = 0;

const initialState = {
  inputMode: 'text' as InputMode,
  inputLanguage: 'vi',
  vietnameseText: '',
  context: '',
  targetLanguage: 'en',
  translatedText: '',
  sourceLanguage: '',
  referenceAudioUri: null as string | null,
  synthesizedAudioUri: null as string | null,
  isTranscribing: false,
  isOcrProcessing: false,
  isTranslating: false,
  isSynthesizing: false,
  isStreaming: false,
  error: null as string | null,
};

// ──────────────────────────────────────────────
// Store
// ──────────────────────────────────────────────

export const useTranslationStore = create<TranslationState>((set, get) => ({
  ...initialState,

  setInputMode: (mode) => set({ inputMode: mode }),

  setInputLanguage: (lang) => {
    if (!supportsSpeechToText(lang)) {
      get().stopStreaming();
    }
    set({ inputLanguage: lang, error: null });
  },

  setVietnameseText: (text) => set({ vietnameseText: text }),

  setContext: (context) => set({ context }),

  setTargetLanguage: (lang) => set({ targetLanguage: lang }),

  transcribeAudio: async (audioUri: string) => {
    const { inputLanguage } = get();
    if (!supportsSpeechToText(inputLanguage)) {
      set({ error: 'Speech-to-text is only available for Vietnamese.' });
      return;
    }
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
    const { targetLanguage, context } = get();
    set({ isOcrProcessing: true, error: null });
    try {
      const result = await apiOcrImage(
        imageUri,
        targetLanguage || undefined,
        undefined,
        context || undefined,
      );
      if (
        result.detected_language &&
        !supportsSpeechToText(result.detected_language)
      ) {
        get().stopStreaming();
      }
      set((state) => ({
        vietnameseText: result.vietnamese_text,
        translatedText: result.translated_text || state.translatedText,
        inputLanguage: result.detected_language || state.inputLanguage,
      }));
    } catch (e: unknown) {
      set({ error: extractErrorMessage(e, 'Failed to process image.') });
    } finally {
      set({ isOcrProcessing: false });
    }
  },

  translate: async () => {
    const { vietnameseText, inputLanguage, targetLanguage, context } = get();
    if (!vietnameseText.trim()) {
      set({ error: 'Please enter or record input text first.' });
      return;
    }
    set({ isTranslating: true, error: null, translatedText: '' });
    try {
      const result = await apiTranslateText(
        vietnameseText,
        targetLanguage,
        inputLanguage,
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

  synthesize: async () => {
    const {
      translatedText,
      targetLanguage,
      referenceAudioUri,
    } = get();
    if (!translatedText.trim()) {
      set({ error: 'Please translate some text first.' });
      return;
    }
    set({ isSynthesizing: true, error: null, synthesizedAudioUri: null });
    try {
      const result = await apiSynthesizeSpeech(
        translatedText,
        targetLanguage,
        referenceAudioUri ?? undefined,
      );
      const localUri = await saveBase64Audio(result.audio_base64, result.format);
      set({ synthesizedAudioUri: localUri });
    } catch (e: unknown) {
      set({ error: extractErrorMessage(e, 'Speech synthesis failed.') });
    } finally {
      set({ isSynthesizing: false });
    }
  },

  startStreaming: async (customUrl?: string) => {
    const { inputLanguage, targetLanguage, context, referenceAudioUri } = get();
    if (!supportsSpeechToText(inputLanguage)) {
      set({
        error: 'Live speech-to-text is only available for Vietnamese.',
        isStreaming: false,
      });
      return;
    }

    const sessionId = streamSessionId + 1;
    streamSessionId = sessionId;

    stopLiveAudioCapture();
    if (activeStreamClient) {
      activeStreamClient.disconnect();
      activeStreamClient = null;
    }
    set({ isStreaming: true, error: null, translatedText: '' });

    const client = new StreamClient({
      sourceLang: inputLanguage,
      targetLang: targetLanguage || 'en',
      customContext: context || '',
      cloneVoice: !!referenceAudioUri,
      onAsrInterim: (text) => {
        if (sessionId === streamSessionId) set({ vietnameseText: text });
      },
      onAsrFinal: (text) => {
        if (sessionId === streamSessionId) set({ vietnameseText: text });
      },
      onTransDelta: (token) => {
        if (sessionId === streamSessionId) {
          set((s) => ({ translatedText: s.translatedText + token }));
        }
      },
      onTransFinal: (text) => {
        if (sessionId === streamSessionId) set({ translatedText: text });
      },
      onAudioChunk: async (b64) => {
        if (sessionId !== streamSessionId) return;
        try {
          const uri = await saveBase64Audio(b64, 'wav');
          if (sessionId === streamSessionId) set({ synthesizedAudioUri: uri });
        } catch {
          // ignore cache write error
        }
      },
      onError: (err) => {
        if (sessionId !== streamSessionId) return;
        streamSessionId += 1;
        stopLiveAudioCapture();
        client.disconnect();
        set({ error: err, isStreaming: false });
      },
      onClose: () => {
        if (sessionId !== streamSessionId) return;
        stopLiveAudioCapture();
        set({ isStreaming: false });
      },
    });

    try {
      await client.connect(customUrl);

      if (sessionId !== streamSessionId || !get().isStreaming) {
        client.disconnect();
        return;
      }

      await startLiveAudioCapture((chunk) => {
        if (sessionId === streamSessionId) client.sendAudioChunk(chunk);
      });

      if (sessionId !== streamSessionId) {
        // A newer session owns the microphone now; only drop the old socket.
        client.disconnect();
        return;
      }

      if (!get().isStreaming) {
        stopLiveAudioCapture();
        client.disconnect();
        return;
      }

      activeStreamClient = client;
    } catch (e: unknown) {
      client.disconnect();
      if (sessionId !== streamSessionId) return;
      streamSessionId += 1;
      stopLiveAudioCapture();
      set({
        error: extractErrorMessage(e, 'Failed to start live microphone streaming.'),
        isStreaming: false,
      });
    }
  },

  stopStreaming: () => {
    streamSessionId += 1;
    stopLiveAudioCapture();
    if (activeStreamClient) {
      activeStreamClient.finish();
      activeStreamClient = null;
    }
    set({ isStreaming: false });
  },

  sendStreamingAudio: (chunk: ArrayBuffer | Uint8Array) => {
    if (activeStreamClient) {
      activeStreamClient.sendAudioChunk(chunk);
    }
  },

  clearError: () => set({ error: null }),

  reset: () => {
    streamSessionId += 1;
    stopLiveAudioCapture();
    if (activeStreamClient) {
      activeStreamClient.disconnect();
      activeStreamClient = null;
    }
    set({ ...initialState });
  },
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
