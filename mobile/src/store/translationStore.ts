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
import {
  DEFAULT_SOURCE_CODE,
  DEFAULT_TARGET_CODE,
  getLanguage,
  LanguageCode,
  TARGET_LANGUAGES,
  supportsSpeechToText,
} from '../constants/languages';
import { strings } from '../constants/strings';
import { buildContext } from '../utils/buildContext';
import { useSettingsStore } from './settingsStore';

// ──────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────

type InputMode = 'text' | 'voice' | 'image';

export type ToneId = 'formal' | 'friendly' | 'academic' | 'business';

type Phase = 'idle' | 'translating' | 'result' | 'error';

export interface TranslationState {
  // ── Input ──
  inputMode: InputMode;
  inputLanguage: string;
  vietnameseText: string;
  context: string;
  targetLanguage: string;

  // ── Output ──
  translatedText: string;
  translatedLanguage: string;
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

  // ── UI state (giao diện mới) ──
  phase: Phase;
  tones: ToneId[];
  contextNote: string;
  contextOpen: boolean;
  translateError: string | null;
  pendingAutoTranslate: boolean;

  // ── Actions ──
  setInputMode: (mode: InputMode) => void;
  setInputLanguage: (lang: string) => void;
  setVietnameseText: (text: string) => void;
  setContext: (context: string) => void;
  setTargetLanguage: (lang: string) => void;
  transcribeAudio: (audioUri: string) => Promise<void>;
  processImage: (imageUri: string) => Promise<void>;
  runOcrOnly: (imageUri: string) => Promise<string>;
  translate: () => Promise<void>;
  setReferenceAudio: (uri: string | null) => void;
  synthesize: () => Promise<void>;
  startStreaming: (customUrl?: string) => Promise<void>;
  stopStreaming: () => void;
  sendStreamingAudio: (chunk: ArrayBuffer | Uint8Array) => void;
  clearError: () => void;
  reset: () => void;

  // ── Actions (giao diện mới) ──
  setText: (text: string) => void;
  clearText: () => void;
  toggleTone: (tone: ToneId) => void;
  setContextNote: (note: string) => void;
  toggleContext: () => void;
  setContextOpen: (open: boolean) => void;
  setSourceLang: (code: string) => void;
  setTargetLang: (code: string) => void;
  requestAutoTranslate: (text: string) => void;
  consumeAutoTranslate: () => boolean;
}

// ──────────────────────────────────────────────
// Default / initial state values
// ──────────────────────────────────────────────

let activeStreamClient: StreamClient | null = null;
let streamSessionId = 0;

const LIVE_STREAM_VOICE_CLONING_ENABLED = false;

const initialState = {
  inputMode: 'text' as InputMode,
  inputLanguage: DEFAULT_SOURCE_CODE,
  vietnameseText: '',
  context: '',
  targetLanguage: DEFAULT_TARGET_CODE,
  translatedText: '',
  translatedLanguage: '',
  sourceLanguage: '',
  referenceAudioUri: null as string | null,
  synthesizedAudioUri: null as string | null,
  isTranscribing: false,
  isOcrProcessing: false,
  isTranslating: false,
  isSynthesizing: false,
  isStreaming: false,
  error: null as string | null,
  phase: 'idle' as Phase,
  tones: [] as ToneId[],
  contextNote: '',
  contextOpen: false,
  translateError: null as string | null,
  pendingAutoTranslate: false,
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
        translatedLanguage:
          result.target_language || state.translatedLanguage,
        // KHÔNG đổi ngôn ngữ nguồn theo `detected_language` (backend dễ nhầm,
        // và người dùng đã chọn nguồn). Giữ nguyên `inputLanguage`.
        inputLanguage: state.inputLanguage,
      }));
    } catch (e: unknown) {
      set({ error: extractErrorMessage(e, 'Failed to process image.') });
    } finally {
      set({ isOcrProcessing: false });
    }
  },

  runOcrOnly: async (imageUri: string): Promise<string> => {
    // Chỉ gọi OCR và trả về chữ đã nhận dạng — KHÔNG ghi vào store, KHÔNG dịch.
    const { targetLanguage } = get();
    const result = await apiOcrImage(imageUri, targetLanguage || undefined);
    return (result.extracted_text ?? '').trim();
  },

  translate: async () => {
    const { vietnameseText, inputLanguage, targetLanguage, tones, contextNote } =
      get();
    if (!vietnameseText.trim()) {
      set({ phase: 'error', translateError: strings.error.generic });
      return;
    }

    const { context, contextPreset } = buildContext(tones, contextNote);

    set({
      isTranslating: true,
      phase: 'translating',
      translateError: null,
      translatedText: '',
    });
    try {
      const result = await apiTranslateText(
        vietnameseText,
        targetLanguage,
        inputLanguage,
        context || undefined,
        contextPreset,
      );
      set({
        translatedText: result.translated_text,
        translatedLanguage: result.target_language,
        sourceLanguage: result.source_language,
        phase: 'result',
      });
    } catch (e: unknown) {
      const message = classifyTranslateError(e);
      set({ phase: 'error', translateError: message });
    } finally {
      set({ isTranslating: false });
    }
  },

  setReferenceAudio: (uri: string | null) => set({ referenceAudioUri: uri }),

  synthesize: async () => {
    const {
      translatedText,
      targetLanguage,
      referenceAudioUri,
      synthesizedAudioUri: previousAudioUri,
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
      const localUri = await saveBase64Audio(
        result.audio_base64,
        result.format,
        previousAudioUri,
      );
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
    set({
      isStreaming: true,
      error: null,
      translatedText: '',
      translatedLanguage: targetLanguage || 'en',
    });

    const client = new StreamClient({
      sourceLang: inputLanguage,
      targetLang: targetLanguage || DEFAULT_TARGET_CODE,
      customContext: context || '',
      cloneVoice: LIVE_STREAM_VOICE_CLONING_ENABLED && !!referenceAudioUri,
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

  // ── Actions (giao diện mới) ──

  setText: (text) => {
    const { phase } = get();
    if (phase === 'result' || phase === 'error') {
      set({ vietnameseText: text, phase: 'idle', translatedText: '', translateError: null });
    } else {
      set({ vietnameseText: text });
    }
  },

  clearText: () =>
    set({
      vietnameseText: '',
      translatedText: '',
      translateError: null,
      phase: 'idle',
    }),

  toggleTone: (tone) => {
    const { tones, phase } = get();
    const next = tones.includes(tone)
      ? tones.filter((t) => t !== tone)
      : [...tones, tone];
    if (phase === 'result' || phase === 'error') {
      set({ tones: next, phase: 'idle', translatedText: '', translateError: null });
    } else {
      set({ tones: next });
    }
  },

  setContextNote: (note) => {
    const trimmed = note.slice(0, 200);
    const { phase } = get();
    if (phase === 'result' || phase === 'error') {
      set({ contextNote: trimmed, phase: 'idle', translatedText: '', translateError: null });
    } else {
      set({ contextNote: trimmed });
    }
  },

  toggleContext: () => set((state) => ({ contextOpen: !state.contextOpen })),

  setContextOpen: (open) => set({ contextOpen: open }),

  setSourceLang: (code) => {
    // Bỏ qua mã không có trong catalog.
    if (!getLanguage(code)) return;
    const { inputLanguage, targetLanguage, phase } = get();
    // Nguồn luôn khác đích: nếu trùng thì hoán đổi (đích ← nguồn cũ).
    const nextTarget: string =
      code === targetLanguage ? inputLanguage : targetLanguage;

    if (phase === 'result' || phase === 'error') {
      set({
        inputLanguage: code,
        targetLanguage: nextTarget,
        phase: 'idle',
        translatedText: '',
        translateError: null,
      });
    } else {
      set({ inputLanguage: code, targetLanguage: nextTarget });
    }

    // Lưu bền thành nguồn mặc định cho lần mở app sau.
    useSettingsStore.getState().setDefaultSourceLang(code as LanguageCode);
  },

  setTargetLang: (code) => {
    // Bỏ qua mã không có trong catalog.
    if (!getLanguage(code)) return;
    const { inputLanguage, targetLanguage, phase } = get();
    // Nguồn luôn khác đích: nếu trùng thì hoán đổi (nguồn ← đích cũ).
    const nextSource: string =
      code === inputLanguage ? targetLanguage : inputLanguage;
    if (phase === 'result' || phase === 'error') {
      set({
        targetLanguage: code,
        inputLanguage: nextSource,
        phase: 'idle',
        translatedText: '',
        translateError: null,
      });
    } else {
      set({ targetLanguage: code, inputLanguage: nextSource });
    }
  },

  requestAutoTranslate: (text) =>
    set({ vietnameseText: text, pendingAutoTranslate: true }),

  consumeAutoTranslate: () => {
    const prev = get().pendingAutoTranslate;
    set({ pendingAutoTranslate: false });
    return prev;
  },
}));

// ──────────────────────────────────────────────
// Utility
// ──────────────────────────────────────────────

/**
 * Kiểm tra lỗi có phải do mạng (axios error không có response, hoặc
 * code ECONNABORTED/ERR_NETWORK). Dùng chung cho nhiều màn.
 */
export function isNetworkError(e: unknown): boolean {
  if (
    typeof e === 'object' &&
    e !== null &&
    'isAxiosError' in e &&
    (e as { isAxiosError: boolean }).isAxiosError
  ) {
    const axiosErr = e as {
      code?: string;
      response?: unknown;
    };
    return (
      !axiosErr.response ||
      axiosErr.code === 'ECONNABORTED' ||
      axiosErr.code === 'ERR_NETWORK'
    );
  }
  return false;
}

/**
 * Phân loại lỗi dịch: lỗi mạng vs lỗi server vs lỗi chung.
 */
function classifyTranslateError(e: unknown): string {
  if (
    typeof e === 'object' &&
    e !== null &&
    'isAxiosError' in e &&
    (e as { isAxiosError: boolean }).isAxiosError
  ) {
    // Lỗi mạng: không có response (mất kết nối) hoặc code network/timeout.
    if (isNetworkError(e)) {
      return strings.error.network;
    }
    // Có response → lấy detail/message từ server.
    return extractErrorMessage(e, strings.error.generic);
  }
  return strings.error.generic;
}

/**
 * Đọc cài đặt mặc định từ settingsStore (sau khi hydrate) và áp vào
 * translationStore. Gọi 1 lần khi app khởi động.
 *
 * - NGUỒN = `defaultSourceLang` đã lưu.
 * - ĐÍCH = `DEFAULT_TARGET_CODE` ('en'), nhưng nếu nguồn là 'en' thì đổi sang
 *   'vi' (hoặc ngôn ngữ ĐÍCH đầu tiên khác nguồn) để nguồn luôn khác đích.
 */
export function applyDefaultsFromSettings(): void {
  const { defaultSourceLang } = useSettingsStore.getState();

  const source =
    (getLanguage(defaultSourceLang)?.canBeSource ?? false)
      ? defaultSourceLang
      : DEFAULT_SOURCE_CODE;

  let target: LanguageCode = DEFAULT_TARGET_CODE;
  if (target === source) {
    // Nguồn là 'en' → đích 'vi' nếu dịch sang tiếng Việt được,
    // ngược lại ngôn ngữ ĐÍCH đầu tiên khác nguồn.
    const vi = TARGET_LANGUAGES.find((l) => l.code === 'vi');
    const firstOther = TARGET_LANGUAGES.find((l) => l.code !== source);
    target = (vi?.code ?? firstOther?.code ?? target) as LanguageCode;
    if (target === source) {
      target = (firstOther?.code ?? target) as LanguageCode;
    }
  }

  useTranslationStore.setState({ inputLanguage: source, targetLanguage: target });
}

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
