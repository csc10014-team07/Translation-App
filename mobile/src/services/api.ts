import axios from 'axios';
import * as FileSystem from 'expo-file-system';
import { API_BASE_URL } from '../config/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
});

// ──────────────────────────────────────────────
// Response interfaces
// ──────────────────────────────────────────────

export interface ASRResponse {
  text: string;
  language_detected: string;
}

export interface OCRResponse {
  vietnamese_text: string;
}

export interface TranslateResponse {
  translated_text: string;
  source_language: string;
  target_language: string;
}

export interface TTSResponse {
  audio_base64: string;
  sample_rate: number;
  format: string;
}

export interface HealthResponse {
  status: string;
  vram: Record<string, unknown>;
}

// ──────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────

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

function getAudioFileInfo(
  uri: string,
  fallbackName: string,
): { fileName: string; mimeType: string } {
  const rawName = uri.split('/').pop()?.split('?')[0] ?? fallbackName;
  const dotIndex = rawName.lastIndexOf('.');
  const ext = dotIndex !== -1 ? rawName.slice(dotIndex + 1).toLowerCase() : 'm4a';
  const fileName = dotIndex !== -1 ? rawName : `${rawName}.${ext}`;

  let mimeType = 'application/octet-stream';
  if (ext === 'm4a' || ext === 'mp4') {
    mimeType = 'audio/mp4';
  } else if (ext === 'wav') {
    mimeType = 'audio/wav';
  } else if (ext === 'mp3') {
    mimeType = 'audio/mpeg';
  } else if (ext === 'flac') {
    mimeType = 'audio/flac';
  } else if (ext === 'ogg') {
    mimeType = 'audio/ogg';
  } else if (ext === 'webm') {
    mimeType = 'audio/webm';
  }

  return { fileName, mimeType };
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
export async function ocrImage(imageUri: string): Promise<OCRResponse> {
  const form = new FormData();
  const fileName = imageUri.split('/').pop() ?? 'image.jpg';
  const ext = fileName.split('.').pop()?.toLowerCase() ?? 'jpg';
  const mimeType = ext === 'png' ? 'image/png' : 'image/jpeg';
  appendFileToForm(form, 'image', imageUri, mimeType, fileName);

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
): Promise<TranslateResponse> {
  const body: { text: string; target_language: string; context?: string } = {
    text,
    target_language: targetLanguage,
  };
  if (context) body.context = context;

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

let lastTtsAudioUri: string | null = null;

/**
 * Decode a base64 audio string returned by TTS and save it to a temp file.
 * Cleans up the previously generated audio file to avoid leaking disk space.
 * Returns the local URI of the saved file.
 */
export async function saveBase64Audio(
  base64: string,
  format: string,
  previousUri?: string | null,
): Promise<string> {
  const fileToDelete = previousUri || lastTtsAudioUri;
  if (fileToDelete) {
    try {
      const info = await FileSystem.getInfoAsync(fileToDelete);
      if (info.exists) {
        await FileSystem.deleteAsync(fileToDelete, { idempotent: true });
      }
    } catch {
      // Ignore cache cleanup failure
    }
  }

  const ext = format ?? 'wav';
  const uri = `${FileSystem.cacheDirectory}tts_output_${Date.now()}.${ext}`;
  await FileSystem.writeAsStringAsync(uri, base64, {
    encoding: FileSystem.EncodingType.Base64,
  });
  lastTtsAudioUri = uri;
  return uri;
}
