/**
 * WebSocket client for real-time speech recognition, translation, and TTS streaming.
 * Connects to /ws/stream over local LAN or Cloudflare Tunnel.
 */
import { getStreamWebSocketUrl } from './api';

export interface StreamEvent {
  event: 'asr_interim' | 'asr_final' | 'trans_delta' | 'trans_final' | 'tts_audio' | 'error';
  text?: string;
  token?: string;
  error?: string;
  audio?: string;
  audio_b64?: string;
}

export interface StreamOptions {
  sourceLang?: string;
  targetLang?: string;
  contextPreset?: string;
  customContext?: string;
  cloneVoice?: boolean;
  onAsrInterim?: (text: string) => void;
  onAsrFinal?: (text: string) => void;
  onTransDelta?: (token: string) => void;
  onTransFinal?: (text: string) => void;
  onError?: (err: string) => void;
  onAudioChunk?: (base64Audio: string) => void;
  onClose?: () => void;
}

export class StreamClient {
  private ws: WebSocket | null = null;
  private options: StreamOptions;

  constructor(options: StreamOptions = {}) {
    this.options = options;
  }

  connect(customUrl?: string): Promise<void> {
    const wsUrl = customUrl || getStreamWebSocketUrl();
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          // Handshake payload as per spec.md contract
          const handshake = {
            action: 'start',
            source_lang: this.options.sourceLang || 'vi',
            target_lang: this.options.targetLang || 'en',
            context_preset: this.options.contextPreset || 'General',
            custom_context: this.options.customContext || '',
            clone_voice: this.options.cloneVoice ?? false,
          };
          this.ws?.send(JSON.stringify(handshake));
          resolve();
        };

        this.ws.onmessage = (event: WebSocketMessageEvent) => {
          try {
            if (typeof event.data === 'string') {
              const data = JSON.parse(event.data);
              switch (data.event) {
                case 'asr_interim':
                  this.options.onAsrInterim?.(data.text);
                  break;
                case 'asr_final':
                  this.options.onAsrFinal?.(data.text);
                  break;
                case 'trans_delta':
                  this.options.onTransDelta?.(data.token || data.delta);
                  break;
                case 'trans_final':
                  this.options.onTransFinal?.(data.text);
                  break;
                case 'tts_audio':
                  if (data.audio_b64 || data.audio) {
                    this.options.onAudioChunk?.(data.audio_b64 || data.audio);
                  }
                  break;
                case 'error':
                  this.options.onError?.(data.error);
                  break;
              }
              const audioPayload = data.audio_b64 || data.audio;
              if (audioPayload && data.event !== 'tts_audio') {
                this.options.onAudioChunk?.(audioPayload);
              }
            }
          } catch {
            // Non-JSON or binary messages handled silently
          }
        };

        this.ws.onerror = (err) => {
          this.options.onError?.('WebSocket connection error');
          reject(err);
        };

        this.ws.onclose = () => {
          this.options.onClose?.();
        };
      } catch (err) {
        reject(err);
      }
    });
  }

  sendAudioChunk(chunk: ArrayBuffer | Uint8Array): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(chunk);
    }
  }

  sendTextMessage(text: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          action: 'translate_text',
          text,
        }),
      );
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
