import React, { useRef, useEffect, useState, useCallback } from 'react';
import {
  View,
  ScrollView,
  Pressable,
  ActivityIndicator,
  AppState,
  Text,
  StyleSheet,
} from 'react-native';
import { Audio } from 'expo-av';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { VoiceListeningScreenProps } from '../navigation/types';
import { useTheme } from '../theme/ThemeProvider';
import ThemedText from '../theme/ThemedText';
import IconCircleButton from '../components/IconCircleButton';
import Waveform from '../components/Waveform';
import { strings } from '../constants/strings';
import { s, vs, ms, MAX_CONTENT_WIDTH } from '../utils/scale';
import { typography } from '../theme/typography';
import { StreamClient } from '../services/stream';
import {
  isLiveAudioSupported,
  startLiveAudioCapture,
  stopLiveAudioCapture,
} from '../services/liveAudio';
import { transcribeAudio as apiTranscribeAudio } from '../services/api';
import { useTranslationStore } from '../store/translationStore';
import { getSourceLabel, DEFAULT_TARGET_CODE } from '../constants/languages';
import { useVoiceRecording } from '../hooks/useVoiceRecording';

type Phase = 'listening' | 'recognizing';

/** Thời gian chờ sự kiện asr_final cuối cùng sau khi gọi finish() (ms). */
const ASR_FINAL_TIMEOUT_MS = 3000;

export default function VoiceListeningScreen({
  navigation,
}: VoiceListeningScreenProps) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const requestAutoTranslate = useTranslationStore((st) => st.requestAutoTranslate);
  // Ngôn ngữ NGUỒN hiện tại — gửi lên ASR/stream và dùng cho dòng gợi ý.
  const inputLanguage = useTranslationStore((st) => st.inputLanguage);

  // Nghe trực tiếp cần native module (development build); Expo Go → ghi rồi nhận dạng.
  const liveSupported = isLiveAudioSupported();

  // ── State hiển thị ──
  const [confirmedText, setConfirmedText] = useState('');
  const [interimText, setInterimText] = useState('');
  const [isListening, setIsListening] = useState(true);
  const [phase, setPhase] = useState<Phase>('listening');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // ── Refs (giá trị mới nhất cho callback bất đồng bộ) ──
  const scrollRef = useRef<ScrollView>(null);
  const confirmedRef = useRef('');
  const interimRef = useRef('');
  const sessionIdRef = useRef(0);
  const streamClientRef = useRef<StreamClient | null>(null);
  const finalWaiterRef = useRef<(() => void) | null>(null);
  const stoppedRef = useRef(false);

  // Ghi âm file (chế độ không live)
  const {
    start: startRecording,
    stop: stopRecording,
    cancel: cancelRecording,
  } = useVoiceRecording();

  const hasText = confirmedText.length > 0 || interimText.length > 0;

  // ── Cuộn xuống cuối mỗi khi có chữ mới ──
  useEffect(() => {
    if (hasText) {
      const t = setTimeout(() => {
        scrollRef.current?.scrollToEnd({ animated: true });
      }, 50);
      return () => clearTimeout(t);
    }
  }, [confirmedText, interimText, hasText]);

  // ── Dọn dẹp tài nguyên thu (idempotent) ──
  const stopEverything = useCallback(() => {
    sessionIdRef.current += 1; // vô hiệu hoá callback phiên hiện tại
    finalWaiterRef.current?.();
    finalWaiterRef.current = null;
    stopLiveAudioCapture();
    if (streamClientRef.current) {
      streamClientRef.current.disconnect();
      streamClientRef.current = null;
    }
    void cancelRecording();
  }, [cancelRecording]);

  // ── Phiên nghe trực tiếp qua WebSocket ──
  const startLiveSession = useCallback(async () => {
    // Xin quyền micro trước — bị từ chối thì dừng và báo lỗi.
    const permission = await Audio.requestPermissionsAsync();
    if (permission.status !== 'granted') {
      setErrorMessage(strings.voice.permissionDenied);
      setIsListening(false);
      return;
    }

    const sessionId = sessionIdRef.current + 1;
    sessionIdRef.current = sessionId;

    const client = new StreamClient({
      sourceLang: inputLanguage,
      targetLang:
        useTranslationStore.getState().targetLanguage || DEFAULT_TARGET_CODE,
      onAsrInterim: (text) => {
        if (sessionId !== sessionIdRef.current) return;
        interimRef.current = text;
        setInterimText(text);
      },
      onAsrFinal: (text) => {
        if (sessionId !== sessionIdRef.current) return;
        const merged = confirmedRef.current
          ? `${confirmedRef.current} ${text}`
          : text;
        confirmedRef.current = merged;
        setConfirmedText(merged);
        interimRef.current = '';
        setInterimText('');
        // Đánh thức người đang chờ asr_final cuối (khi bấm dừng).
        finalWaiterRef.current?.();
      },
      // Màn này chỉ cần chữ nhận dạng — bỏ qua trans_* / tts_audio.
      onTransDelta: () => undefined,
      onTransFinal: () => undefined,
      onAudioChunk: () => undefined,
      onError: (err) => {
        if (sessionId !== sessionIdRef.current) return;
        setErrorMessage(err);
        setIsListening(false);
      },
    });

    streamClientRef.current = client;

    try {
      await client.connect();
      if (sessionId !== sessionIdRef.current) {
        client.disconnect();
        return;
      }
      await startLiveAudioCapture((chunk) => {
        if (sessionId === sessionIdRef.current) client.sendAudioChunk(chunk);
      });
    } catch {
      if (sessionId !== sessionIdRef.current) return;
      client.disconnect();
      if (streamClientRef.current === client) streamClientRef.current = null;
      setErrorMessage(strings.error.generic);
      setIsListening(false);
    }
  }, [inputLanguage]);

  // ── Phiên ghi âm file (Expo Go) ──
  const startRecordingSession = useCallback(async () => {
    try {
      await startRecording();
    } catch (e) {
      if (e instanceof Error && e.message === 'MICROPHONE_PERMISSION_DENIED') {
        setErrorMessage(strings.voice.permissionDenied);
      } else {
        setErrorMessage(strings.error.generic);
      }
      setIsListening(false);
    }
  }, [startRecording]);

  // ── Bắt đầu phiên khi màn mount ──
  useEffect(() => {
    stoppedRef.current = false;
    if (liveSupported) {
      void startLiveSession();
    } else {
      void startRecordingSession();
    }
    // Chỉ chạy 1 lần khi mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Dọn khi unmount ──
  useEffect(() => {
    return () => {
      stopEverything();
    };
  }, [stopEverything]);

  // ── Dọn khi app xuống nền (không để micro mở ngầm) ──
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (state !== 'active') stopEverything();
    });
    return () => sub.remove();
  }, [stopEverything]);

  // ── Nghe lại (đổi nguồn / không nhận được chữ) → xoá phiên cũ, bắt đầu lại ──
  const restartListening = useCallback(async () => {
    stopEverything(); // tăng sessionId → mọi kết quả phiên cũ bị bỏ
    stoppedRef.current = false;
    confirmedRef.current = '';
    interimRef.current = '';
    setConfirmedText('');
    setInterimText('');
    setPhase('listening');
    setIsListening(true);
    if (liveSupported) {
      await startLiveSession();
    } else {
      await startRecordingSession();
    }
  }, [liveSupported, startLiveSession, startRecordingSession, stopEverything]);

  // ── Nguồn đổi giữa phiên → bỏ kết quả cũ, bắt đầu phiên theo ngôn ngữ mới ──
  const sessionLanguageRef = useRef(inputLanguage);
  useEffect(() => {
    if (sessionLanguageRef.current === inputLanguage) return;
    sessionLanguageRef.current = inputLanguage;
    if (!stoppedRef.current) {
      setErrorMessage(null);
      void restartListening();
    }
  }, [inputLanguage, restartListening]);

  // ── Nút DỪNG: chốt chữ rồi yêu cầu dịch ──
  const handleStop = useCallback(async () => {
    if (stoppedRef.current || phase === 'recognizing') return;
    stoppedRef.current = true;

    const mySession = sessionIdRef.current;
    setErrorMessage(null);
    setIsListening(false);
    setPhase('recognizing');

    if (liveSupported) {
      stopLiveAudioCapture();
      const client = streamClientRef.current;

      // Chờ asr_final cuối tối đa ASR_FINAL_TIMEOUT_MS.
      const finalPromise = new Promise<void>((resolve) => {
        finalWaiterRef.current = resolve;
      });
      const timer = setTimeout(() => {
        finalWaiterRef.current?.();
        finalWaiterRef.current = null;
      }, ASR_FINAL_TIMEOUT_MS);

      client?.finish(ASR_FINAL_TIMEOUT_MS);
      await finalPromise;
      clearTimeout(timer);
      finalWaiterRef.current = null;

      if (sessionIdRef.current !== mySession) return; // đã bị huỷ
      if (streamClientRef.current === client) streamClientRef.current = null;
      client?.disconnect();
    } else {
      const uri = await stopRecording();
      if (uri) {
        try {
          const result = await apiTranscribeAudio(uri, inputLanguage);
          // Vô hiệu nếu nguồn đổi giữa chừng → bỏ kết quả của nguồn cũ.
          if (sessionIdRef.current !== mySession) return;
          const text = result.text?.trim() ?? '';
          if (text) {
            const merged = confirmedRef.current
              ? `${confirmedRef.current} ${text}`
              : text;
            confirmedRef.current = merged;
            setConfirmedText(merged);
          }
        } catch {
          // Coi như không nhận được chữ.
        }
      }
      if (sessionIdRef.current !== mySession) return; // đã bị huỷ
    }

    const text = `${confirmedRef.current} ${interimRef.current}`.trim();
    if (!text) {
      // Không có chữ → báo và nghe lại (không đóng màn).
      setErrorMessage(strings.voice.noSpeech);
      void restartListening();
      return;
    }

    // Có chữ → nhờ Home tự dịch, rồi đóng màn.
    sessionIdRef.current += 1;
    requestAutoTranslate(text);
    navigation.goBack();
  }, [
    phase,
    liveSupported,
    stopRecording,
    restartListening,
    requestAutoTranslate,
    navigation,
    inputLanguage,
  ]);

  // ── Nút ×: huỷ toàn bộ, KHÔNG đổi vietnameseText ──
  const handleCancel = useCallback(() => {
    stopEverything();
    navigation.goBack();
  }, [stopEverything, navigation]);

  return (
    <View style={[styles.safe, { backgroundColor: colors.background }]}>
      <View style={styles.contentWrapper}>
        {/* ── HÀNG ĐẦU ── */}
        <View style={[styles.topRow, { paddingTop: insets.top + vs(8) }]}>
          <ThemedText style={[styles.title, { color: colors.textPrimary }]}>
            {phase === 'recognizing'
              ? strings.voice.recognizing
              : strings.voice.listening}
          </ThemedText>
          <IconCircleButton
            icon="close"
            size="small"
            variant="neutral"
            accessibilityLabel={strings.accessibility.close}
            onPress={handleCancel}
          />
        </View>

        {/* ── DÒNG GỢI Ý ── */}
        <ThemedText
          style={[styles.hint, { color: colors.textSecondary, marginTop: vs(14) }]}
        >
          {liveSupported
            ? strings.voice.hint(getSourceLabel(inputLanguage))
            : strings.voice.hintNoLive(getSourceLabel(inputLanguage))}
        </ThemedText>

        {/* ── CARD CHỨA CHỮ NHẬN DẠNG ── */}
        <View
          style={[
            styles.textCard,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
              marginTop: vs(18),
            },
          ]}
        >
          <ScrollView
            ref={scrollRef}
            showsVerticalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
          >
            {/* Thông báo lỗi / không nghe thấy */}
            {errorMessage !== null && (
              <ThemedText
                style={[styles.errorText, { color: colors.danger }]}
              >
                {errorMessage}
              </ThemedText>
            )}

            {/* Chữ nhận dạng: confirmed (đậm) + interim (xám) + "…" */}
            {hasText && (
              <Text
                style={[styles.recognizedText, typography.bodyLarge]}
                maxFontSizeMultiplier={1.2}
              >
                {confirmedText.length > 0 && (
                  <Text style={{ color: colors.textPrimary }}>{confirmedText}</Text>
                )}
                {interimText.length > 0 && (
                  <Text style={{ color: colors.interimText }}>
                    {confirmedText.length > 0 ? ` ${interimText}` : interimText}…
                  </Text>
                )}
              </Text>
            )}
          </ScrollView>
        </View>

        {/* ── NHÓM ĐIỀU KHIỂN ── */}
        <View
          style={[styles.controls, { marginBottom: vs(16) + insets.bottom }]}
        >
          <Waveform active={isListening} />

          {/* Nút dừng (halo + nút trong + biểu tượng) */}
          <Pressable
            onPress={handleStop}
            disabled={phase === 'recognizing'}
            accessibilityRole="button"
            accessibilityLabel={strings.voice.tapToStop}
            style={({ pressed }) => [
              styles.halo,
              {
                marginTop: vs(14),
                backgroundColor: colors.primarySoft,
                opacity: pressed ? 0.85 : 1,
              },
            ]}
          >
            <View style={[styles.stopButton, { backgroundColor: colors.primary }]}>
              {phase === 'recognizing' ? (
                <ActivityIndicator color={colors.onPrimary} />
              ) : (
                <View style={[styles.stopSquare, { backgroundColor: colors.onPrimary }]} />
              )}
            </View>
          </Pressable>

          {/* Chú thích */}
          <ThemedText
            style={[styles.stopHint, { color: colors.textSecondary, marginTop: vs(10) }]}
          >
            {strings.voice.tapToStop}
          </ThemedText>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
  },
  contentWrapper: {
    flex: 1,
    width: '100%',
    maxWidth: MAX_CONTENT_WIDTH,
    alignSelf: 'center',
    paddingHorizontal: s(21),
  },

  // ── Hàng đầu ──
  topRow: {
    minHeight: s(46),
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {
    fontSize: ms(24),
    fontWeight: '700',
  },

  // ── Gợi ý ──
  hint: {
    fontSize: ms(16),
    fontWeight: '400',
  },

  // ── Card chữ nhận dạng ──
  textCard: {
    flex: 1,
    borderWidth: 1,
    borderRadius: s(24),
    padding: s(22),
  },
  recognizedText: {
    // Typography áp inline (typography.bodyLarge)
  },
  errorText: {
    fontSize: ms(16),
    lineHeight: ms(24),
    fontWeight: '400',
  },

  // ── Nhóm điều khiển ──
  controls: {
    alignItems: 'center',
    marginTop: vs(14),
  },
  halo: {
    width: s(114),
    height: s(114),
    borderRadius: s(114) / 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stopButton: {
    width: s(93),
    height: s(93),
    borderRadius: s(93) / 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stopSquare: {
    width: s(30),
    height: s(30),
    borderRadius: s(6),
  },
  stopHint: {
    fontSize: ms(14),
    fontWeight: '400',
  },
});
