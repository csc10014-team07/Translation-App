import axios from 'axios';
import * as FileSystem from 'expo-file-system';
import { API_BASE_URL, WS_BASE_URL } from '../config/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
});

/**
 * Resolves the real-time WebSocket streaming endpoint.
 * Automatically translates http(s) to ws(s) if needed.
 */
export function getStreamWebSocketUrl(): string {
  if (typeof WS_BASE_URL === 'string' && WS_BASE_URL.length > 0) {
    return WS_BASE_URL;
  }
  const isHttps = API_BASE_URL.startsWith('https://');
  const proto = isHttps ? 'wss://' : 'ws://';
  const cleanHost = API_BASE_URL.replace(/^https?:\/\//, '').replace(/\/+$/, '');
  return `${proto}${cleanHost}/ws/stream`;
}


// ──────────────────────────────────────────────
// Response interfaces
// ──────────────────────────────────────────────

export interface ASRResponse {
  text: string;
  language_detected: string;
}

export interface OCRResponse {
  vietnamese_text: string;
  extracted_text?: string;
  detected_language?: string;
  target_language?: string;
  translated_text?: string;
  boxes?: unknown[];
  elapsed_ms?: number;
}

export interface TranslateResponse {
  translated_text: string;
  source_language: string;
  target_language: string;
  engine_used?: string;
  elapsed_ms?: number;
}

export interface TTSResponse {
  audio_base64: string;
  sample_rate: number;
  format: string;
}

export interface HealthResponse {
  status: string;
  device?: string;
  vram: Record<string, unknown>;
}

// ──────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────

const AUDIO_MIME_MAP: Record<string, string> = {
  m4a: 'audio/mp4',
  mp4: 'audio/mp4',
  mp3: 'audio/mpeg',
  wav: 'audio/wav',
  flac: 'audio/flac',
  ogg: 'audio/ogg',
  webm: 'audio/webm',
};

export function getAudioFileInfo(
  uri: string,
  fallbackName: string,
): { fileName: string; mimeType: string } {
  const dotIndex = uri.lastIndexOf('.');
  const ext = dotIndex !== -1 ? uri.substring(dotIndex + 1).toLowerCase() : 'm4a';
  const mimeType = AUDIO_MIME_MAP[ext] ?? 'application/octet-stream';
  const lastPart = uri.split('/').pop()?.split('?')[0];
  const fileName = lastPart && lastPart.includes('.')
    ? lastPart
    : (fallbackName.includes('.') ? fallbackName : `${fallbackName}.${ext}`);
  return { fileName, mimeType };
}

/**
 * Read a local file URI and append it as a multipart field.
 * expo-file-system is used to convert the uri into a blob-compatible object
 * that React Native's FormData understands.
 */
function appendFileToForm(
  form: FormData,
  fieldName: string,
  uri: string,
  mimeType: string,
  fileName: string,
): void {
  // React Native FormData accepts { uri, name, type } objects directly
  form.append(fieldName, {
    uri,
    name: fileName,
    type: mimeType,
  } as unknown as Blob);
}

// ──────────────────────────────────────────────
// API functions
// ──────────────────────────────────────────────

/**
 * POST /api/asr — send an audio file and get back Vietnamese text.
 */
export async function transcribeAudio(audioUri: string): Promise<ASRResponse> {
  const form = new FormData();
  const { fileName, mimeType } = getAudioFileInfo(audioUri, 'recording.m4a');
  appendFileToForm(form, 'audio', audioUri, mimeType, fileName);

  const response = await apiClient.post<ASRResponse>('/api/asr', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

/**
 * POST /api/ocr — send an image file and get back Vietnamese text.
 */
export async function ocrImage(
  imageUri: string,
  targetLanguage?: string,
  contextPreset?: string,
  customContext?: string,
): Promise<OCRResponse> {
  const form = new FormData();
  const fileName = imageUri.split('/').pop() ?? 'image.jpg';
  const ext = fileName.split('.').pop()?.toLowerCase() ?? 'jpg';
  const mimeType = ext === 'png' ? 'image/png' : 'image/jpeg';
  appendFileToForm(form, 'image', imageUri, mimeType, fileName);

  if (targetLanguage) form.append('target_language', targetLanguage);
  if (contextPreset) form.append('context_preset', contextPreset);
  if (customContext) form.append('custom_context', customContext);

  const response = await apiClient.post<OCRResponse>('/api/ocr', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

/**
 * POST /api/translate — translate Vietnamese text to the target language.
 */
export async function translateText(
  text: string,
  targetLanguage: string,
  context?: string,
  contextPreset?: string,
  customContext?: string,
): Promise<TranslateResponse> {
  const body: {
    text: string;
    target_language: string;
    context?: string;
    context_preset?: string;
    custom_context?: string;
  } = {
    text,
    target_language: targetLanguage,
  };
  if (context) body.context = context;
  if (contextPreset) body.context_preset = contextPreset;
  if (customContext) body.custom_context = customContext;

  const response = await apiClient.post<TranslateResponse>(
    '/api/translate',
    body,
  );
  return response.data;
}

/**
 * POST /api/tts — synthesize speech, optionally with a reference voice.
 */
export async function synthesizeSpeech(
  text: string,
  language: string,
  referenceAudioUri?: string,
): Promise<TTSResponse> {
  const form = new FormData();
  form.append('text', text);
  form.append('language', language);

  if (referenceAudioUri) {
    const { fileName, mimeType } = getAudioFileInfo(
      referenceAudioUri,
      'reference.m4a',
    );
    appendFileToForm(
      form,
      'reference_audio',
      referenceAudioUri,
      mimeType,
      fileName,
    );
  }

  const response = await apiClient.post<TTSResponse>('/api/tts', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

/**
 * GET /health — check backend availability.
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>('/health');
  return response.data;
}

/**
 * Decode a base64 audio string returned by TTS and save it to a temp file.
 * Returns the local URI of the saved file.
 */
export async function saveBase64Audio(
  base64: string,
  format: string,
): Promise<string> {
  const ext = format ?? 'wav';
  const timestamp = Date.now();
  const uri = `${FileSystem.cacheDirectory}tts_output_${timestamp}.${ext}`;
  await FileSystem.writeAsStringAsync(uri, base64, {
    encoding: FileSystem.EncodingType.Base64,
  });
  
  // Cleanup: delete old TTS files (keep only the current one)
  try {
    const cacheDir = FileSystem.cacheDirectory;
    if (cacheDir) {
      const files = await FileSystem.readDirectoryAsync(cacheDir);
      const ttsFiles = files.filter(f => f.startsWith('tts_output_') && f.endsWith(`.${ext}`));
      for (const file of ttsFiles) {
        if (file !== `tts_output_${timestamp}.${ext}`) {
          const fileUri = `${cacheDir}${file}`;
          await FileSystem.deleteAsync(fileUri);
        }
      }
    }
  } catch (error) {
    // Ignore cleanup errors
  }
  
  return uri;
}
