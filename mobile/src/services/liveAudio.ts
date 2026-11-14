/**
 * Live microphone capture for the /ws/stream WebSocket endpoint.
 *
 * react-native-live-audio-stream emits base64-encoded 16-bit PCM frames. It is a
 * native module, so live streaming requires a development/production build
 * (it is not available in Expo Go).
 */
import { Audio } from 'expo-av';
import { NativeModules } from 'react-native';

export type LiveAudioChunkHandler = (chunk: Uint8Array) => void;

const SAMPLE_RATE_HZ = 16000;
const CHANNEL_COUNT = 1;
const BITS_PER_SAMPLE = 16;
// 100ms of 16kHz mono 16-bit audio, matching the backend VAD chunk size.
const BUFFER_SIZE_BYTES = 3200;
const ANDROID_VOICE_RECOGNITION = 6;
const BASE64_RADIX = 4;
const BASE64_PAD_CHAR = '=';
const BASE64_PAD_CODE = BASE64_PAD_CHAR.charCodeAt(0);
const BASE64_ALPHABET =
  'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
const BYTE_MASK = 0xff;
const BYTE_SHIFT_16 = 16;
const BYTE_SHIFT_8 = 8;
const BITS_PER_BASE64_CHAR = 6;
const BASE64_LOOKUP = buildBase64Lookup();

interface LiveAudioStreamOptions {
  sampleRate: number;
  channels: number;
  bitsPerSample: number;
  audioSource?: number;
  wavFile: string;
  bufferSize?: number;
}

interface LiveAudioStreamModule {
  init: (options: LiveAudioStreamOptions) => void;
  start: () => void;
  stop: () => Promise<string> | void;
  on: (event: 'data', callback: (data: string) => void) => void;
}

let streamModule: LiveAudioStreamModule | null = null;
let activeHandler: LiveAudioChunkHandler | null = null;
let listenerRegistered = false;
let isCapturing = false;
let captureGeneration = 0;

export function isLiveAudioSupported(): boolean {
  return Boolean(NativeModules.RNLiveAudioStream);
}

function loadStreamModule(): LiveAudioStreamModule {
  if (streamModule) return streamModule;

  if (!isLiveAudioSupported()) {
    throw new Error(
      'Live microphone streaming needs a development build. Rebuild the app after installing native modules.',
    );
  }

  // Lazy require so Expo Go does not evaluate the native module at startup.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const loaded = require('react-native-live-audio-stream') as {
    default?: LiveAudioStreamModule;
  };
  const module = loaded.default;
  if (!module) {
    throw new Error('Live microphone streaming module failed to load.');
  }
  streamModule = module;
  return module;
}

async function ensureMicrophonePermission(): Promise<void> {
  const permission = await Audio.requestPermissionsAsync();
  if (permission.status !== 'granted') {
    throw new Error(
      permission.canAskAgain
        ? 'Microphone permission is required for live streaming.'
        : 'Microphone permission denied. Enable it in Settings.',
    );
  }
}

function buildBase64Lookup(): Int16Array {
  const lookup = new Int16Array(256).fill(-1);
  for (let index = 0; index < BASE64_ALPHABET.length; index += 1) {
    lookup[BASE64_ALPHABET.charCodeAt(index)] = index;
  }
  return lookup;
}

function decodeBase64Pcm(base64: string): Uint8Array {
  const cleaned = base64.trim();
  if (!cleaned) return new Uint8Array(0);

  let padding = 0;
  if (cleaned.endsWith(`${BASE64_PAD_CHAR}${BASE64_PAD_CHAR}`)) {
    padding = 2;
  } else if (cleaned.endsWith(BASE64_PAD_CHAR)) {
    padding = 1;
  }

  const outputLength = Math.max(
    0,
    (cleaned.length * 3) / BASE64_RADIX - padding,
  );
  const output = new Uint8Array(outputLength);
  let outputIndex = 0;

  for (let index = 0; index < cleaned.length; index += BASE64_RADIX) {
    const c0 = BASE64_LOOKUP[cleaned.charCodeAt(index)];
    const c1 = BASE64_LOOKUP[cleaned.charCodeAt(index + 1)];
    if (c0 < 0 || c1 < 0) continue;

    const c2 =
      cleaned.charCodeAt(index + 2) === BASE64_PAD_CODE
        ? 0
        : BASE64_LOOKUP[cleaned.charCodeAt(index + 2)];
    const c3 =
      cleaned.charCodeAt(index + 3) === BASE64_PAD_CODE
        ? 0
        : BASE64_LOOKUP[cleaned.charCodeAt(index + 3)];
    const triplet =
      (c0 << (BITS_PER_BASE64_CHAR * 3)) |
      (c1 << (BITS_PER_BASE64_CHAR * 2)) |
      ((c2 < 0 ? 0 : c2) << BITS_PER_BASE64_CHAR) |
      (c3 < 0 ? 0 : c3);

    if (outputIndex < outputLength) {
      output[outputIndex] = (triplet >> BYTE_SHIFT_16) & BYTE_MASK;
      outputIndex += 1;
    }
    if (outputIndex < outputLength) {
      output[outputIndex] = (triplet >> BYTE_SHIFT_8) & BYTE_MASK;
      outputIndex += 1;
    }
    if (outputIndex < outputLength) {
      output[outputIndex] = triplet & BYTE_MASK;
      outputIndex += 1;
    }
  }

  return outputIndex === outputLength ? output : output.subarray(0, outputIndex);
}

export async function startLiveAudioCapture(
  onChunk: LiveAudioChunkHandler,
): Promise<void> {
  if (isCapturing) {
    activeHandler = onChunk;
    return;
  }

  const stream = loadStreamModule();
  const generation = captureGeneration + 1;
  captureGeneration = generation;

  await ensureMicrophonePermission();
  if (generation !== captureGeneration) return;

  await Audio.setAudioModeAsync({
    allowsRecordingIOS: true,
    playsInSilentModeIOS: true,
    staysActiveInBackground: false,
    shouldDuckAndroid: true,
  });
  if (generation !== captureGeneration) return;

  stream.init({
    sampleRate: SAMPLE_RATE_HZ,
    channels: CHANNEL_COUNT,
    bitsPerSample: BITS_PER_SAMPLE,
    audioSource: ANDROID_VOICE_RECOGNITION,
    bufferSize: BUFFER_SIZE_BYTES,
    wavFile: '',
  });

  if (!listenerRegistered) {
    stream.on('data', (data) => {
      activeHandler?.(decodeBase64Pcm(data));
    });
    listenerRegistered = true;
  }

  activeHandler = onChunk;
  stream.start();
  isCapturing = true;
}

export function stopLiveAudioCapture(): void {
  captureGeneration += 1;
  activeHandler = null;
  if (!isCapturing) return;
  isCapturing = false;

  try {
    void Promise.resolve(streamModule?.stop()).catch(() => undefined);
  } catch {
    // The native recorder may already be stopped.
  }

  void Audio.setAudioModeAsync({ allowsRecordingIOS: false }).catch(
    () => undefined,
  );
}
