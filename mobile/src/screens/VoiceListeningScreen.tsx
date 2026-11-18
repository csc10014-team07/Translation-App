/**
 * VoiceListeningScreen — màn ghi âm / nhận dạng giọng nói.
 *
 * Ba phase: idle → listening → recognizing (do useVoiceSession quản lý).
 * Nút micro (idle)   → start()
 * Nút dừng (listen)  → stopManual(goBack)   ← finalize('manual') → requestAutoTranslate → goBack
 * Nút × (mọi phase) → cancel() + goBack()   ← không dịch
 */
import React, { useRef, useEffect } from 'react';
import {
  View,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Text,
  StyleSheet,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import type { VoiceListeningScreenProps } from '../navigation/types';
import { useTheme } from '../theme/ThemeProvider';
import ThemedText from '../theme/ThemedText';
import IconCircleButton from '../components/IconCircleButton';
import Waveform from '../components/Waveform';
import { strings } from '../constants/strings';
import { s, vs, ms, MAX_CONTENT_WIDTH } from '../utils/scale';
import { typography } from '../theme/typography';
import { useTranslationStore } from '../store/translationStore';
import { getSourceLabel } from '../constants/languages';
import { VOICE_WARNING_REMAINING_S } from '../constants/voice';
import { formatMmSs } from '../utils/formatTime';
import { useVoiceSession } from '../hooks/useVoiceSession';

export default function VoiceListeningScreen({
  navigation,
}: VoiceListeningScreenProps) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();

  // Chỉ dùng ngôn ngữ nguồn để dựng dòng gợi ý.
  const inputLanguage = useTranslationStore((st) => st.inputLanguage);

  const {
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
  } = useVoiceSession();

  // ── Cuộn xuống cuối mỗi khi có chữ mới ──────────────────────────────────
  const scrollRef = useRef<ScrollView>(null);
  const hasText = confirmedText.length > 0 || interimText.length > 0;

  useEffect(() => {
    if (hasText) {
      const t = setTimeout(
        () => scrollRef.current?.scrollToEnd({ animated: true }),
        50,
      );
      return () => clearTimeout(t);
    }
  }, [confirmedText, interimText, hasText]);

  // ── Tiêu đề, gợi ý, chú thích theo phase ────────────────────────────────
  const title =
    phase === 'idle'
      ? strings.voice.idleTitle
      : phase === 'recognizing'
        ? strings.voice.recognizing
        : strings.voice.listening;

  const hintText =
    limitHint !== null
      ? limitHint // "Đã đạt thời gian tối đa, đang dịch…"
      : phase === 'idle'
        ? strings.voice.idleHint
        : phase === 'recognizing'
          ? strings.voice.recognizingHint
          : liveSupported
            ? strings.voice.hint(getSourceLabel(inputLanguage))
            : strings.voice.hintNoLive(getSourceLabel(inputLanguage));

  const isWarning =
    phase === 'listening' && maxS - elapsedS <= VOICE_WARNING_REMAINING_S;

  // ── Handlers ─────────────────────────────────────────────────────────────
  const goBack = useRef(() => navigation.goBack()).current;

  const handleMainButton = () => {
    if (phase === 'idle') {
      // Truyền goBack cho cả trường hợp timer tự hết giờ
      void start(goBack);
    } else if (phase === 'listening') {
      // Truyền goBack làm onDone; hook gọi sau khi nhận dạng xong
      stopManual(goBack);
    }
    // recognizing → nút disabled
  };

  const handleCancel = () => {
    cancel();
    navigation.goBack();
  };

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <View style={[styles.safe, { backgroundColor: colors.background }]}>
      <View style={styles.contentWrapper}>

        {/* ── HÀNG ĐẦU ── */}
        <View style={[styles.topRow, { paddingTop: insets.top + vs(8) }]}>
          <ThemedText style={[styles.title, { color: colors.textPrimary }]}>
            {title}
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
          style={[
            styles.hint,
            { color: colors.textSecondary, marginTop: vs(14) },
          ]}
        >
          {hintText}
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
          {/* Thông báo lỗi nhỏ */}
          {message !== null && (
            <ThemedText style={[styles.errorText, { color: colors.danger }]}>
              {message}
            </ThemedText>
          )}

          {/* Placeholder khi idle và không có chữ */}
          {phase === 'idle' && !hasText && message === null && (
            <View style={styles.cardCenter}>
              <ThemedText
                numberOfLines={2}
                style={[styles.cardPlaceholder, { color: colors.placeholder }]}
              >
                {strings.voice.idleCardHint}
              </ThemedText>
            </View>
          )}

          {/* Placeholder khi listening nhưng chưa có chữ */}
          {phase === 'listening' && !hasText && message === null && (
            <ThemedText style={[styles.infoText, { color: colors.placeholder }]}>
              {strings.voice.listeningPlaceholder}
            </ThemedText>
          )}

          {/* Chữ nhận dạng: confirmed + interim + "…" */}
          {hasText && (
            <ScrollView
              ref={scrollRef}
              showsVerticalScrollIndicator={false}
              keyboardShouldPersistTaps="handled"
            >
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
            </ScrollView>
          )}
        </View>

        {/* ── NHÓM ĐIỀU KHIỂN ── */}
        <View style={[styles.controls, { marginBottom: vs(16) + insets.bottom }]}>
          <Waveform active={phase === 'listening'} />

          {/* Nút halo + nút tròn bên trong */}
          <Pressable
            onPress={handleMainButton}
            disabled={phase === 'recognizing'}
            accessibilityRole="button"
            accessibilityLabel={
              phase === 'idle'
                ? strings.voice.tapToStart
                : strings.voice.tapToStop
            }
            style={({ pressed }) => [
              styles.halo,
              {
                marginTop: vs(14),
                backgroundColor: colors.primarySoft,
                opacity: pressed && phase !== 'recognizing' ? 0.85 : 1,
              },
            ]}
          >
            <View style={[styles.mainButton, { backgroundColor: colors.primary }]}>
              {phase === 'idle' && (
                <Ionicons name="mic" size={ms(40)} color={colors.onPrimary} />
              )}
              {phase === 'listening' && (
                <View
                  style={[styles.stopSquare, { backgroundColor: colors.onPrimary }]}
                />
              )}
              {phase === 'recognizing' && (
                <ActivityIndicator color={colors.onPrimary} />
              )}
            </View>
          </Pressable>

          {/* Bộ đếm giờ — chỉ khi listening */}
          {phase === 'listening' && (
            <ThemedText
              style={[
                styles.timer,
                {
                  color: isWarning ? colors.danger : colors.textSecondary,
                  fontWeight: isWarning ? '600' : '400',
                  marginTop: vs(8),
                },
              ]}
            >
              {`${formatMmSs(elapsedS)} / ${formatMmSs(maxS)}`}
            </ThemedText>
          )}

          {/* Chú thích dưới nút */}
          <ThemedText
            style={[
              styles.stopHint,
              {
                color: colors.textSecondary,
                marginTop: phase === 'listening' ? vs(4) : vs(10),
              },
            ]}
          >
            {phase === 'idle'
              ? strings.voice.tapToStart
              : phase === 'recognizing'
                ? strings.voice.recognizingCaption
                : strings.voice.tapToStop}
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
  cardCenter: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardPlaceholder: {
    fontSize: ms(20),
    fontWeight: '400',
    textAlign: 'center',
  },
  recognizedText: {
    // Typography áp inline
  },
  errorText: {
    fontSize: ms(15),
    lineHeight: ms(22),
    fontWeight: '400',
  },
  infoText: {
    fontSize: ms(15),
    lineHeight: ms(22),
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
  mainButton: {
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
  timer: {
    fontSize: ms(14),
  },
  stopHint: {
    fontSize: ms(14),
    fontWeight: '400',
  },
});
