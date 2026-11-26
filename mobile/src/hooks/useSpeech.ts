/**
 * useSpeech — hook quản lý toàn bộ logic đọc to (TTS) cho thẻ kết quả.
 *
 * Trả về:
 *   status: 'idle' | 'loading' | 'playing' | 'error'
 *   ttsError: string | null           — thông báo lỗi nhỏ hiển thị dưới nút
 *   play()                            — gọi TTS / phát (toggle)
 *   stop()                            — dừng phát
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Audio, AVPlaybackStatus } from 'expo-av';
import {
  synthesizeSpeech,
  saveBase64Audio,
} from '../services/api';
import { supportsTts } from '../constants/languages';
import { strings } from '../constants/strings';

export type SpeechStatus = 'idle' | 'loading' | 'playing' | 'error';

interface UseSpeechResult {
  status: SpeechStatus;
  ttsError: string | null;
  ttsNote: string | null;
  play: () => Promise<void>;
  stop: () => Promise<void>;
}

/**
 * @param text           — bản dịch cần đọc
 * @param language       — mã ngôn ngữ đích (e.g. 'en', 'ja')
 * @param enabled        — true khi phase === 'result'; false thì không làm gì
 * @param referenceAudioUri — giọng mẫu trong phiên; null = giọng mặc định
 */
export function useSpeech(
  text: string,
  language: string,
  enabled: boolean,
  referenceAudioUri: string | null = null,
): UseSpeechResult {
  const [status, setStatus] = useState<SpeechStatus>('idle');
  const [ttsError, setTtsError] = useState<string | null>(null);
  const [ttsNote, setTtsNote] = useState<string | null>(null);

  // Sound instance hiện tại
  const soundRef = useRef<Audio.Sound | null>(null);
  // Cache: key = text + language + reference → uri + note
  const cacheRef = useRef<Map<string, { uri: string; note: string | null }>>(
    new Map(),
  );
  // Theo dõi key của lần fetch gần nhất để tránh race condition
  const fetchKeyRef = useRef<string>('');

  // ── Dọn Sound khi unmount hoặc khi text/language/enabled thay đổi ──
  const unloadSound = useCallback(async () => {
    const snd = soundRef.current;
    soundRef.current = null;
    if (snd) {
      try {
        await snd.stopAsync();
        await snd.unloadAsync();
      } catch {
        // Bỏ qua lỗi unload
      }
    }
  }, []);

  useEffect(() => {
    // Reset về idle mỗi khi đầu vào thay đổi hoặc widget bị ẩn
    setStatus('idle');
    setTtsError(null);
    setTtsNote(null);
    void unloadSound();
  }, [text, language, enabled, referenceAudioUri, unloadSound]);

  // Dọn khi unmount
  useEffect(() => {
    return () => {
      void unloadSound();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Cấu hình audio mode một lần ──
  useEffect(() => {
    void Audio.setAudioModeAsync({
      playsInSilentModeIOS: true,
      staysActiveInBackground: false,
      allowsRecordingIOS: false,
    });
  }, []);

  // ── Callback khi playback thay đổi ──
  const handlePlaybackStatus = useCallback((playbackStatus: AVPlaybackStatus) => {
    if (!playbackStatus.isLoaded) return;
    if (playbackStatus.didJustFinish) {
      setStatus('idle');
    }
  }, []);

  // ── stop ──
  const stop = useCallback(async () => {
    const snd = soundRef.current;
    if (!snd) return;
    try {
      await snd.stopAsync();
      await snd.setPositionAsync(0);
    } catch {
      // Bỏ qua lỗi stop
    }
    setStatus('idle');
  }, []);

  // ── play (toggle: nếu đang phát thì dừng, ngược lại phát) ──
  const play = useCallback(async () => {
    if (!enabled) return;

    // Ngôn ngữ đích không có giọng đọc → không gọi API, báo lỗi ngay.
    if (!supportsTts(language)) {
      setStatus('error');
      setTtsError(strings.home.ttsUnsupported);
      return;
    }

    // Đang phát → dừng
    if (status === 'playing') {
      await stop();
      return;
    }

    setStatus('loading');
    setTtsError(null);
    setTtsNote(null);

    const cacheKey = `${text}|${language}|${referenceAudioUri ?? 'default'}`;
    fetchKeyRef.current = cacheKey;

    try {
      // Lấy URI từ cache hoặc gọi API
      let cached = cacheRef.current.get(cacheKey);

      if (!cached) {
        const ttsResponse = await synthesizeSpeech(
          text,
          language,
          referenceAudioUri ?? undefined,
        );
        // Race condition: người dùng đổi bản dịch/giọng khi đang fetch
        if (fetchKeyRef.current !== cacheKey) return;

        const uri = await saveBase64Audio(
          ttsResponse.audio_base64,
          ttsResponse.format,
        );
        if (fetchKeyRef.current !== cacheKey) return;

        let note: string | null = null;
        if (ttsResponse.reference_used) {
          note = ttsResponse.voice_cloned
            ? strings.home.voiceClonedNote
            : strings.home.voiceCloneFallbackNote;
        }
        cached = { uri, note };
        cacheRef.current.set(cacheKey, cached);
      }

      // Dọn Sound cũ (nếu có)
      await unloadSound();

      const { sound } = await Audio.Sound.createAsync(
        { uri: cached.uri },
        { shouldPlay: true },
        handlePlaybackStatus,
      );
      soundRef.current = sound;
      setTtsNote(cached.note);
      setStatus('playing');
    } catch {
      setStatus('error');
      setTtsError('Không đọc được. Thử lại.');
    }
  }, [
    enabled,
    status,
    text,
    language,
    referenceAudioUri,
    stop,
    unloadSound,
    handlePlaybackStatus,
  ]);

  return { status, ttsError, ttsNote, play, stop };
}
