/**
 * useVoiceSession — quản lý toàn bộ vòng đời một phiên ghi/nghe giọng nói.
 *
 * Trả về:
 *   phase          — 'idle' | 'listening' | 'recognizing'
 *   confirmedText  — chữ đã chốt (asr_final hoặc kết quả /api/asr)
 *   interimText    — chữ tạm (asr_interim, chỉ live mode)
 *   elapsedS       — số giây đã nghe (0 nếu idle/recognizing)
 *   maxS           — thời lượng tối đa của chế độ hiện tại (đã trừ safety margin)
 *   message        — thông báo lỗi hoặc null
 *   limitHint      — hint riêng khi dừng do vượt giờ ('limit'), null bình thường
 *   liveSupported  — true nếu native module RNLiveAudioStream có mặt
 *   start()        — bắt đầu nghe (xin quyền micro tại đây)
 *   stopManual()   — kích hoạt finalize('manual')
 *   cancel()       — huỷ toàn bộ, xoá chữ; dùng cho ×, unmount, AppState
 */

import { useRef, useState, useCallback, useEffect } from 'react';
import { AppState, AccessibilityInfo } from 'react-native';
import { Audio } from 'expo-av';

import { StreamClient } from '../services/stream';
import { transcribeAudio as apiTranscribeAudio } from '../services/api';
import {
  isLiveAudioSupported,
  startLiveAudioCapture,
  stopLiveAudioCapture,
} from '../services/liveAudio';
import { useVoiceRecording } from './useVoiceRecording';
import { useTranslationStore } from '../store/translationStore';
import { DEFAULT_TARGET_CODE } from '../constants/languages';
import {
  getVoiceMaxDurationS,
  VOICE_FINAL_WAIT_MS,
  VOICE_WARNING_REMAINING_S,
} from '../constants/voice';
import { INPUT_MAX_LENGTH } from '../constants/limits';
import { strings } from '../constants/strings';

// ── Tên ASR nguồn cố định vì PhoASR chỉ hỗ trợ tiếng Việt ─────────────────
const ASR_SOURCE_LANG = 'vi';

// ── Bộ đếm giờ: cập nhật 4 lần/giây để mượt ────────────────────────────────
const TIMER_INTERVAL_MS = 250;

// ── Kiểu trạng thái phiên ───────────────────────────────────────────────────
export type VoicePhase = 'idle' | 'listening' | 'recognizing';

export type FinalizeReason = 'manual' | 'limit';

export interface UseVoiceSessionResult {
  phase: VoicePhase;
  confirmedText: string;
  interimText: string;
  /** Số giây đã nghe; 0 khi idle hoặc recognizing. */
  elapsedS: number;
  /** Thời lượng tối đa (giây) cho chế độ hiện tại, đã trừ safety margin. */
  maxS: number;
  /** Thông báo lỗi nhỏ hiển thị trong card, hoặc null. */
  message: string | null;
  /**
   * Hint riêng khi dừng vì vượt giờ: "Đã đạt thời gian tối đa, đang dịch…"
   * Null trong mọi trường hợp khác.
   */
  limitHint: string | null;
  liveSupported: boolean;
  /**
   * Bắt đầu nghe — xin quyền micro tại đây.
   * onDone sẽ được gọi khi phiên kết thúc tự động (hết giờ) và đã gọi
   * requestAutoTranslate. Truyền navigation.goBack().
   */
  start: (onDone: () => void) => Promise<void>;
  /**
   * Dừng thủ công → finalize('manual'): nhận dạng xong rồi gọi onDone.
   * onDone do màn truyền vào để gọi navigation.goBack() sau khi requestAutoTranslate.
   */
  stopManual: (onDone: () => void) => void;
  /** Huỷ toàn bộ, xoá chữ. Dùng cho ×, unmount, AppState background. */
  cancel: () => void;
}

export function useVoiceSession(): UseVoiceSessionResult {
  const liveSupported = isLiveAudioSupported();
  const maxS = getVoiceMaxDurationS(liveSupported);

  // ── State React ──────────────────────────────────────────────────────────
  const [phase, setPhase] = useState<VoicePhase>('idle');
  const [confirmedText, setConfirmedText] = useState('');
  const [interimText, setInterimText] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [limitHint, setLimitHint] = useState<string | null>(null);
  const [elapsedS, setElapsedS] = useState(0);

  // ── Refs (không re-render) ───────────────────────────────────────────────
  /** Tăng mỗi khi bắt đầu phiên mới; dùng để bỏ qua callback của phiên cũ. */
  const sessionIdRef = useRef(0);
  const confirmedRef = useRef('');
  const interimRef = useRef('');
  const streamClientRef = useRef<StreamClient | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTsRef = useRef(0);
  /** Cờ chống gọi finalize() hai lần trong cùng phiên (bấm dừng + hết giờ). */
  const finalizingRef = useRef(false);
  /** Đã thông báo accessibility cảnh báo 5 giây chưa. */
  const warnedRef = useRef(false);
  /** Resolve của Promise chờ asr_final cuối trong live mode. */
  const finalWaiterRef = useRef<(() => void) | null>(null);
  /**
   * Callback gọi khi finalize xong (thường = navigation.goBack).
   * Màn gán khi gọi stopManual(); timer dùng khi hết giờ.
   */
  const onDoneRef = useRef<(() => void) | null>(null);
  /** Cờ chống bấm trùng start() khi phase chưa kịp cập nhật. */
  const startingRef = useRef(false);

  // ── Hook ghi âm file (Expo Go) ───────────────────────────────────────────
  const {
    stop: stopRecording,
    cancel: cancelRecording,
    start: startRecording,
  } = useVoiceRecording();

  // ── Dừng bộ đếm ─────────────────────────────────────────────────────────
  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  // ── Dừng capture (không đụng state phase/text) ──────────────────────────
  const stopCaptureOnly = useCallback(() => {
    stopTimer();
    stopLiveAudioCapture();
    finalWaiterRef.current?.();
    finalWaiterRef.current = null;
    if (streamClientRef.current) {
      streamClientRef.current.disconnect();
      streamClientRef.current = null;
    }
    void cancelRecording();
  }, [cancelRecording, stopTimer]);

  // ── finalize(reason) ─────────────────────────────────────────────────────
  /**
   * Hàm nội bộ, chạy đúng một lần mỗi phiên (finalizingRef làm cờ chặn).
   * Nhận dạng xong → requestAutoTranslate → onDone().
   * An toàn: sau MỖI await kiểm tra sessionIdRef.current === sessionId.
   * Nếu cancel() đã chạy (sessionId thay đổi) → KHÔNG gọi requestAutoTranslate, KHÔNG gọi onDone.
   */
  const finalize = useCallback(
    async (reason: FinalizeReason, sessionId: number, onDone: () => void) => {
      // Chặn gọi trùng
      if (finalizingRef.current) return;
      finalizingRef.current = true;

      // 1. Chuyển phase recognizing, dừng thu
      stopTimer();
      stopLiveAudioCapture();

      if (reason === 'limit') {
        setLimitHint(strings.voice.limitReached);
      }
      setPhase('recognizing');
      setElapsedS(0);

      // 2. Thu kết quả cuối
      if (liveSupported) {
        // Live: gọi finish() rồi chờ asr_final cuối tối đa VOICE_FINAL_WAIT_MS
        const client = streamClientRef.current;
        const finalPromise = new Promise<void>((resolve) => {
          finalWaiterRef.current = resolve;
        });
        const timeoutId = setTimeout(() => {
          finalWaiterRef.current?.();
          finalWaiterRef.current = null;
        }, VOICE_FINAL_WAIT_MS);

        client?.finish(VOICE_FINAL_WAIT_MS);
        await finalPromise;
        // Kiểm tra session sau await
        if (sessionIdRef.current !== sessionId) {
          clearTimeout(timeoutId);
          finalWaiterRef.current = null;
          finalizingRef.current = false;
          return;
        }
        clearTimeout(timeoutId);
        finalWaiterRef.current = null;

        if (streamClientRef.current === client) {
          client?.disconnect();
          streamClientRef.current = null;
        }
      } else {
        // File: dừng recorder rồi gửi lên /api/asr
        const uri = await stopRecording();
        // Kiểm tra session sau await
        if (sessionIdRef.current !== sessionId) {
          finalizingRef.current = false;
          return;
        }
        if (uri) {
          try {
            const result = await apiTranscribeAudio(uri, ASR_SOURCE_LANG);
            // Kiểm tra session sau await
            if (sessionIdRef.current !== sessionId) {
              finalizingRef.current = false;
              return;
            }
            const text = result.text?.trim() ?? '';
            if (text) {
              const merged = confirmedRef.current
                ? `${confirmedRef.current} ${text}`
                : text;
              confirmedRef.current = merged;
              setConfirmedText(merged);
            }
          } catch (e) {
            // Kiểm tra session sau await
            if (sessionIdRef.current !== sessionId) {
              finalizingRef.current = false;
              return;
            }
            // HTTP 422 = audio vượt thời lượng backend
            const status =
              typeof e === 'object' && e !== null
                ? (
                    e as {
                      response?: { status?: number };
                    }
                  ).response?.status
                : undefined;
            if (status === 422) {
              setMessage(strings.voice.tooLong);
            } else {
              setMessage(strings.error.generic);
            }
            setLimitHint(null);
            setPhase('idle');
            finalizingRef.current = false;
            return;
          }
        }
      }

      // Kiểm tra session trước khi xử lý text cuối
      if (sessionIdRef.current !== sessionId) {
        finalizingRef.current = false;
        return;
      }

      // 3. Ghép text và cắt ở INPUT_MAX_LENGTH (ranh giới từ)
      let text = `${confirmedRef.current} ${interimRef.current}`.trim();
      if (text.length > INPUT_MAX_LENGTH) {
        const cut = text.lastIndexOf(' ', INPUT_MAX_LENGTH);
        text = cut > 0 ? text.slice(0, cut) : text.slice(0, INPUT_MAX_LENGTH);
      }

      if (!text) {
        setMessage(strings.voice.noSpeech);
        setLimitHint(null);
        setPhase('idle');
        finalizingRef.current = false;
        return;
      }

      // 4. Yêu cầu dịch và đóng màn (chỉ khi session vẫn hiện hành)
      useTranslationStore.getState().requestAutoTranslate(text);
      // Kiểm tra lần cuối: nếu cancel() đã xóa onDoneRef → không goBack
      if (sessionIdRef.current === sessionId && onDoneRef.current !== null) {
        onDone(); // → navigation.goBack()
      }
    },
    [liveSupported, stopRecording, stopTimer],
  );

  // ── Dừng & dọn toàn bộ (idempotent) ────────────────────────────────────
  const stopAll = useCallback(
    (clearText: boolean) => {
      sessionIdRef.current += 1;
      finalizingRef.current = false;
      warnedRef.current = false;
      stopCaptureOnly();
      finalWaiterRef.current = null;

      if (clearText) {
        confirmedRef.current = '';
        interimRef.current = '';
        setConfirmedText('');
        setInterimText('');
        setMessage(null);
        setLimitHint(null);
      }
      setElapsedS(0);
    },
    [stopCaptureOnly],
  );

  // ── start() ──────────────────────────────────────────────────────────────
  const start = useCallback(async (onDone: () => void) => {
    // Chống bấm trùng: dùng ref để check ngay lập tức (phase state chưa cập nhật kịp)
    if (phase !== 'idle' || startingRef.current) return;
    startingRef.current = true;

    // Ghi lại onDone để timer dùng khi hết giờ
    onDoneRef.current = onDone;

    // 1. Xin quyền micro ngay tại đây
    const permission = await Audio.requestPermissionsAsync();
    if (permission.status !== 'granted') {
      startingRef.current = false;
      setMessage(strings.voice.permissionDenied);
      return;
    }

    // 2. Reset phiên cũ
    stopAll(false);
    confirmedRef.current = '';
    interimRef.current = '';
    setConfirmedText('');
    setInterimText('');
    setMessage(null);
    setLimitHint(null);
    finalizingRef.current = false;
    warnedRef.current = false;
    startingRef.current = false;

    const sessionId = sessionIdRef.current; // đã tăng bởi stopAll

    setPhase('listening');

    // 3. Rẽ nhánh theo chế độ
    if (liveSupported) {
      // ── LIVE: StreamClient + PCM chunks ──────────────────────────────
      const client = new StreamClient({
        sourceLang: ASR_SOURCE_LANG,
        targetLang:
          useTranslationStore.getState().targetLanguage || DEFAULT_TARGET_CODE,
        onAsrInterim: (text) => {
          if (sessionIdRef.current !== sessionId) return;
          interimRef.current = text;
          setInterimText(text);
        },
        onAsrFinal: (text) => {
          if (sessionIdRef.current !== sessionId) return;
          const merged = confirmedRef.current
            ? `${confirmedRef.current} ${text}`
            : text;
          confirmedRef.current = merged;
          setConfirmedText(merged);
          interimRef.current = '';
          setInterimText('');
          // Đánh thức người đang chờ asr_final cuối trong finalize()
          finalWaiterRef.current?.();
          finalWaiterRef.current = null;
        },
        onTransDelta: () => undefined,
        onTransFinal: () => undefined,
        onAudioChunk: () => undefined,
        onError: (err) => {
          if (sessionIdRef.current !== sessionId) return;
          stopTimer();
          // Map technical error to user-friendly message
          const msg =
            err?.includes('WebSocket') || err?.includes('network') || err?.includes('connection')
              ? strings.voice.networkError
              : err;
          setMessage(msg);
          setPhase('idle');
        },
        onClose: () => {
          if (sessionIdRef.current !== sessionId) return;
          stopTimer();
          setPhase('idle');
        },
      });

      streamClientRef.current = client;

      try {
        await client.connect();
        if (sessionIdRef.current !== sessionId) {
          client.disconnect();
          return;
        }
        await startLiveAudioCapture((chunk) => {
          if (sessionIdRef.current === sessionId) {
            client.sendAudioChunk(chunk);
          }
        });
        if (sessionIdRef.current !== sessionId) return;
        // Bắt đầu đếm giờ SAU khi capture đã mở thành công
        // (onDone sẽ được gán khi stopManual gọi; timer tự gọi finalize khi hết giờ)
        // Cần truyền onDone vào timer — dùng ref để tránh closure cũ
      } catch (e) {
        if (sessionIdRef.current !== sessionId) return;
        if (streamClientRef.current === client) streamClientRef.current = null;
        client.disconnect();
        stopTimer();
        // Phân loại lỗi kết nối vs lỗi khác
        const errMsg =
          e instanceof Error &&
          (e.message.includes('WebSocket') ||
            e.message.includes('network') ||
            e.message.includes('connection') ||
            e.message.includes('fetch'))
            ? strings.voice.networkError
            : strings.error.generic;
        setMessage(errMsg);
        setPhase('idle');
        return;
      }
    } else {
      // ── FILE: expo-av ghi âm ──────────────────────────────────────────
      try {
        await startRecording();
        if (sessionIdRef.current !== sessionId) {
          void cancelRecording();
          return;
        }
      } catch (e) {
        if (sessionIdRef.current !== sessionId) return;
        stopTimer();
        setMessage(
          e instanceof Error && e.message === 'MICROPHONE_PERMISSION_DENIED'
            ? strings.voice.permissionDenied
            : strings.error.generic,
        );
        setPhase('idle');
        return;
      }
    }

    // Bộ đếm giờ — onDone lúc này chưa có (sẽ gán khi stopManual).
    // Timer finalize khi hết giờ cần onDone: dùng onDoneRef để cập nhật sau.
    startTsRef.current = Date.now();
    warnedRef.current = false;
    setElapsedS(0);

    timerRef.current = setInterval(() => {
      const elapsed = (Date.now() - startTsRef.current) / 1000;
      setElapsedS(Math.floor(elapsed));

      const remaining = maxS - elapsed;
      if (!warnedRef.current && remaining <= VOICE_WARNING_REMAINING_S) {
        warnedRef.current = true;
        void AccessibilityInfo.announceForAccessibility(
          strings.voice.warningAnnounce,
        );
      }

      if (elapsed >= maxS && !finalizingRef.current) {
        const cb = onDoneRef.current;
        if (cb) void finalize('limit', sessionId, cb);
      }
    }, TIMER_INTERVAL_MS);
  }, [
    phase,
    liveSupported,
    stopAll,
    stopTimer,
    startRecording,
    cancelRecording,
    maxS,
    finalize,
  ]);

  // ── stopManual() ─────────────────────────────────────────────────────────
  const stopManual = useCallback(
    (onDone: () => void) => {
      if (phase !== 'listening') return;
      onDoneRef.current = onDone;
      void finalize('manual', sessionIdRef.current, onDone);
    },
    [phase, finalize],
  );

  // ── cancel() ─────────────────────────────────────────────────────────────
  const cancel = useCallback(() => {
    stopAll(true);
    startingRef.current = false;
    onDoneRef.current = null;
    setPhase('idle');
    setLimitHint(null);
  }, [stopAll]);

  // ── Dọn khi unmount ──────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      sessionIdRef.current += 1;
      finalizingRef.current = false;
      startingRef.current = false;
      if (timerRef.current) clearInterval(timerRef.current);
      finalWaiterRef.current?.();
      finalWaiterRef.current = null;
      stopLiveAudioCapture();
      if (streamClientRef.current) {
        streamClientRef.current.disconnect();
        streamClientRef.current = null;
      }
      void cancelRecording();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Dọn khi app xuống nền ────────────────────────────────────────────────
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (state !== 'active') cancel();
    });
    return () => sub.remove();
  }, [cancel]);

  return {
    phase,
    confirmedText,
    interimText,
    elapsedS,
    maxS,
    message,
    limitHint,
    liveSupported,
    start,
    stopManual,
    cancel,
  };
}
