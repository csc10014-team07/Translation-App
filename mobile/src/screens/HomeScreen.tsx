import React, { useRef, useCallback, useEffect, useState } from 'react';
import {
  View,
  Pressable,
  ScrollView,
  TextInput,
  KeyboardAvoidingView,
  Keyboard,
  LayoutAnimation,
  Platform,
  UIManager,
  AccessibilityInfo,
  StyleSheet,
} from 'react-native';
import * as Clipboard from 'expo-clipboard';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import type { HomeScreenProps } from '../navigation/types';
import { useTheme } from '../theme/ThemeProvider';
import ThemedText from '../theme/ThemedText';
import IconCircleButton from '../components/IconCircleButton';
import LanguageTile from '../components/LanguageTile';
import ToneChip from '../components/ToneChip';
import PrimaryButton from '../components/PrimaryButton';
import ErrorCard from '../components/ErrorCard';
import { strings } from '../constants/strings';
import {
  getSourceFullLabel,
  getSourceLabel,
  getTargetLabel,
  supportsOcr,
  supportsTts,
  supportsVoiceInput,
} from '../constants/languages';
import { INPUT_MAX_LENGTH } from '../constants/limits';
import {
  useTranslationStore,
  applyDefaultsFromSettings,
  ToneId,
} from '../store/translationStore';
import { useSettingsStore } from '../store/settingsStore';
import { s, vs, ms, MAX_CONTENT_WIDTH } from '../utils/scale';
import { typography } from '../theme/typography';
import { useSpeech } from '../hooks/useSpeech';

// Bật LayoutAnimation cho Android
if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

// Danh sách 4 giọng văn theo thứ tự hiển thị
const TONES: { id: ToneId; label: string }[] = [
  { id: 'formal', label: strings.tones.formal },
  { id: 'friendly', label: strings.tones.friendly },
  { id: 'academic', label: strings.tones.academic },
  { id: 'business', label: strings.tones.business },
];

/** Thời gian tự ẩn dòng thông báo nhỏ dưới ô nhập (ms). */
const INPUT_HINT_HIDE_MS = 3000;

export default function HomeScreen({ navigation }: HomeScreenProps) {
  const { colors, mode, toggleMode } = useTheme();
  const insets = useSafeAreaInsets();

  // ── Store ──
  const inputLanguage = useTranslationStore((st) => st.inputLanguage);
  const targetLanguage = useTranslationStore((st) => st.targetLanguage);
  const vietnameseText = useTranslationStore((st) => st.vietnameseText);
  const phase = useTranslationStore((st) => st.phase);
  const setText = useTranslationStore((st) => st.setText);
  const clearText = useTranslationStore((st) => st.clearText);
  const tones = useTranslationStore((st) => st.tones);
  const toggleTone = useTranslationStore((st) => st.toggleTone);
  const contextNote = useTranslationStore((st) => st.contextNote);
  const setContextNote = useTranslationStore((st) => st.setContextNote);
  const contextOpen = useTranslationStore((st) => st.contextOpen);
  const toggleContext = useTranslationStore((st) => st.toggleContext);
  const translate = useTranslationStore((st) => st.translate);

  // ── Trạng thái copy ──
  const [copied, setCopied] = useState(false);
  const copyTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Dòng thông báo nhỏ dưới ô nhập (ví dụ: nguồn không hỗ trợ mic/quét chữ) ──
  const [inputHint, setInputHint] = useState<string | null>(null);
  const inputHintTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Dọn timeout copy + thông báo khi unmount
  useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
      if (inputHintTimeoutRef.current) clearTimeout(inputHintTimeoutRef.current);
    };
  }, []);

  /** Hiện dòng thông báo nhỏ dưới ô nhập, tự ẩn sau 3 giây, đọc cho screen reader. */
  const showInputHint = useCallback((message: string) => {
    setInputHint(message);
    AccessibilityInfo.announceForAccessibility(message);
    if (inputHintTimeoutRef.current) clearTimeout(inputHintTimeoutRef.current);
    inputHintTimeoutRef.current = setTimeout(
      () => setInputHint(null),
      INPUT_HINT_HIDE_MS,
    );
  }, []);

  // ── Áp ngôn ngữ đích mặc định 1 lần, sau khi settingsStore hydrate xong ──
  const hasHydrated = useSettingsStore((st) => st.hasHydrated);
  const appliedDefaultsRef = useRef(false);
  useEffect(() => {
    if (hasHydrated && !appliedDefaultsRef.current) {
      appliedDefaultsRef.current = true;
      applyDefaultsFromSettings();
    }
  }, [hasHydrated]);

  // ── Khi Home được focus lại: nếu có cờ chờ dịch tự động (từ Giọng nói/Camera) ──
  useFocusEffect(
    useCallback(() => {
      const { pendingAutoTranslate, vietnameseText: text } =
        useTranslationStore.getState();
      if (pendingAutoTranslate) {
        const consumed = useTranslationStore.getState().consumeAutoTranslate();
        if (consumed && text.trim().length > 0) {
          Keyboard.dismiss();
          void translate();
        }
      }
    }, [translate]),
  );

  // ── TTS (đọc to) ──
  const translatedText = useTranslationStore((st) => st.translatedText);
  const translateError = useTranslationStore((st) => st.translateError);
  const { status: speechStatus, ttsError, play: playSpeech } = useSpeech(
    translatedText,
    targetLanguage,
    phase === 'result',
  );

  const inputRef = useRef<TextInput>(null);
  const scrollRef = useRef<ScrollView>(null);
  const errorCardYRef = useRef<number>(0);

  const hasText = vietnameseText.length > 0;
  const cardMinHeight =
    hasText || phase === 'result' || phase === 'error' ? vs(200) : vs(248);

  const hasContext = tones.length > 0 || contextNote.trim().length > 0;
  const contextSummary =
    tones.length > 0
      ? tones.map((id) => TONES.find((t) => t.id === id)?.label ?? id).join(', ')
      : strings.home.contextNoteFallback;

  // Nút Dịch chỉ hiện ở phase idle / translating
  const showTranslateBar = phase === 'idle' || phase === 'translating';

  // Ngôn ngữ đích có giọng đọc (TTS) hay không — quyết định hiện nút "Đọc to".
  const ttsSupported = supportsTts(targetLanguage);

  // ── Mở / đóng thẻ ngữ cảnh với animation ──
  const handleToggleContext = useCallback(() => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    toggleContext();
  }, [toggleContext]);

  // Khi mở thẻ ngữ cảnh → cuộn xuống để thấy hết
  useEffect(() => {
    if (contextOpen) {
      const t = setTimeout(() => {
        scrollRef.current?.scrollToEnd({ animated: true });
      }, 120);
      return () => clearTimeout(t);
    }
  }, [contextOpen]);

  // Khi có lỗi → cuộn ErrorCard vào tầm nhìn + thông báo cho screen reader
  useEffect(() => {
    if (phase === 'error') {
      const t = setTimeout(() => {
        scrollRef.current?.scrollTo({
          y: Math.max(errorCardYRef.current - vs(16), 0),
          animated: true,
        });
        if (translateError) {
          AccessibilityInfo.announceForAccessibility(
            `${strings.error.translateTitle}. ${translateError}`,
          );
        }
      }, 120);
      return () => clearTimeout(t);
    }
  }, [phase, translateError]);

  const handleClear = useCallback(() => {
    clearText();
    inputRef.current?.focus();
  }, [clearText]);

  // ── Mic: chỉ mở màn Giọng nói khi nguồn hỗ trợ ASR ──
  const handleMic = useCallback(() => {
    if (!supportsVoiceInput(inputLanguage)) {
      showInputHint(strings.voice.unsupported(getSourceLabel(inputLanguage)));
      return;
    }
    navigation.navigate('VoiceListening');
  }, [inputLanguage, showInputHint, navigation]);

  // ── Camera: chỉ mở màn quét chữ khi nguồn hỗ trợ OCR ──
  const handleCamera = useCallback(() => {
    if (!supportsOcr(inputLanguage)) {
      showInputHint(strings.camera.ocrUnsupported(getSourceLabel(inputLanguage)));
      return;
    }
    navigation.navigate('Camera');
  }, [inputLanguage, showInputHint, navigation]);

  const handleTranslate = useCallback(() => {
    Keyboard.dismiss();
    translate();
  }, [translate]);

  const handleCopy = useCallback(() => {
    void Clipboard.setStringAsync(translatedText);
    setCopied(true);
    AccessibilityInfo.announceForAccessibility(strings.home.copied);
    if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
    copyTimeoutRef.current = setTimeout(() => setCopied(false), 1500);
  }, [translatedText]);

  return (
    // KeyboardAvoidingView bao toàn màn — đẩy nội dung lên trên bàn phím
    <KeyboardAvoidingView
      style={[styles.kav, { backgroundColor: colors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      // Trên iOS cần offset bằng chiều cao safe-area trên (header chưa tính trong inset)
      keyboardVerticalOffset={Platform.OS === 'ios' ? insets.top : 0}
    >
      {/* Wrapper căn giữa + paddingHorizontal — không bao gồm thanh nút Dịch */}
      <View style={styles.inner}>

        {/* ── Phần cố định trên (header + hàng ngôn ngữ) ── */}
        <View style={[styles.topFixed, { paddingTop: insets.top }]}>
          <View style={styles.contentWrapper}>

            {/* HEADER */}
            <View style={styles.header}>
              <ThemedText variant="title">{strings.home.title}</ThemedText>
              <IconCircleButton
                icon={mode === 'light' ? 'sunny-outline' : 'moon-outline'}
                size="small"
                variant="neutral"
                accessibilityLabel={strings.accessibility.toggleTheme}
                onPress={toggleMode}
              />
            </View>

            {/* HÀNG NGÔN NGỮ */}
            <View style={[styles.languageRow, { marginTop: vs(14) }]}>
              {/* Thẻ "Dịch từ" — bấm để chọn ngôn ngữ nguồn */}
              <LanguageTile
                label={strings.home.from}
                value={getSourceLabel(inputLanguage)}
                onPress={() => navigation.navigate('SourceLanguage')}
                accessibilityLabel={`${strings.home.from} ${getSourceFullLabel(
                  inputLanguage,
                )}, ${strings.accessibility.changeTarget}`}
              />

              {/* Mũi tên giữa */}
              <View style={styles.arrowWrap}>
                <Ionicons name="arrow-forward" size={ms(20)} color={colors.textSecondary} />
              </View>

              {/* Thẻ "Dịch sang" */}
              <LanguageTile
                label={strings.home.to}
                value={getTargetLabel(targetLanguage)}
                onPress={() => navigation.navigate('TargetLanguage')}
                accessibilityLabel={`${strings.home.to} ${getTargetLabel(
                  targetLanguage,
                )}, ${strings.accessibility.changeTarget}`}
              />
            </View>
          </View>
        </View>

        {/* ── SCROLL AREA (flex 1, cuộn được kể cả khi bàn phím mở) ── */}
        <ScrollView
          ref={scrollRef}
          style={styles.scrollArea}
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="on-drag"
          showsVerticalScrollIndicator={false}
          contentContainerStyle={[
            styles.scrollContent,
            // Khi ẩn thanh nút Dịch (có kết quả/lỗi), chừa thêm safe-area đáy
            // để thẻ cuối không nằm dưới thanh gesture/điều hướng.
            !showTranslateBar && { paddingBottom: vs(24) + insets.bottom },
          ]}
        >
          <View style={styles.contentWrapper}>

            {/* Ô NHẬP VĂN BẢN */}
            <View
              style={[
                styles.inputCard,
                {
                  backgroundColor: colors.surface,
                  borderColor: colors.border,
                  minHeight: cardMinHeight,
                },
              ]}
            >
              <TextInput
                ref={inputRef}
                multiline
                value={vietnameseText}
                onChangeText={setText}
                placeholder={strings.home.placeholder}
                placeholderTextColor={colors.placeholder}
                maxLength={INPUT_MAX_LENGTH}
                textAlignVertical="top"
                maxFontSizeMultiplier={1.2}
                style={[
                  styles.textInput,
                  typography.bodyLarge,
                  {
                    color: colors.textPrimary,
                    paddingRight: hasText ? s(40) : s(22),
                  },
                ]}
              />

              {/* Nút xoá — chỉ hiện khi có chữ */}
              {hasText && (
                <Pressable
                  onPress={handleClear}
                  accessibilityLabel={strings.accessibility.clear}
                  accessibilityRole="button"
                  hitSlop={s(6)}
                  style={[styles.clearButton, { top: vs(20), right: s(22) }]}
                >
                  <Ionicons name="close" size={ms(22)} color={colors.textSecondary} />
                </Pressable>
              )}

              {/* 2 nút tròn góc dưới-trái */}
              <View style={[styles.inputActions, { left: s(22), bottom: vs(13) }]}>
                <IconCircleButton
                  icon="mic-outline"
                  size="medium"
                  variant="soft"
                  accessibilityLabel={strings.accessibility.mic}
                  onPress={handleMic}
                />
                <View style={{ width: s(11) }} />
                <IconCircleButton
                  icon="camera-outline"
                  size="medium"
                  variant="soft"
                  accessibilityLabel={strings.accessibility.camera}
                  onPress={handleCamera}
                />
              </View>

              {/* Spacer đẩy nội dung tránh đè lên 2 nút tròn */}
              <View style={{ height: vs(76) }} />
            </View>

            {/* DÒNG THÔNG BÁO NHỎ NGAY DƯỚI Ô NHẬP — tự ẩn sau 3 giây */}
            {inputHint !== null && (
              <ThemedText
                accessibilityLiveRegion="polite"
                style={[
                  styles.inputHint,
                  { color: colors.textSecondary, marginTop: vs(10) },
                ]}
              >
                {inputHint}
              </ThemedText>
            )}

            {/* THẺ KẾT QUẢ — chỉ hiện khi phase === 'result' */}
            {phase === 'result' && (
              <View
                style={[
                  styles.resultCard,
                  {
                    backgroundColor: colors.surface,
                    borderColor: colors.border,
                    marginTop: vs(14),
                  },
                ]}
              >
                {/* Nhãn ngôn ngữ đích */}
                <ThemedText style={[styles.resultLang, { color: colors.primary }]}>
                  {getTargetLabel(targetLanguage)}
                </ThemedText>

                {/* Bản dịch */}
                <ThemedText
                  style={[
                    styles.resultText,
                    typography.result,
                    { color: colors.textPrimary, marginTop: vs(14) },
                  ]}
                  selectable
                >
                  {translatedText}
                </ThemedText>

                {/* Hàng nút: Đọc to (chỉ khi ngôn ngữ đích có giọng) + Sao chép */}
                <View style={[styles.resultActions, { marginTop: vs(16) }]}>
                  {ttsSupported && (
                    <>
                      <PrimaryButton
                        variant="pill"
                        label={
                          speechStatus === 'playing'
                            ? strings.home.stopReading
                            : strings.home.readAloud
                        }
                        iconLeft={
                          speechStatus === 'playing'
                            ? 'stop'
                            : 'volume-medium-outline'
                        }
                        loading={speechStatus === 'loading'}
                        onPress={playSpeech}
                      />
                      <View style={{ width: s(12) }} />
                    </>
                  )}
                  <IconCircleButton
                    icon={copied ? 'checkmark' : 'copy-outline'}
                    size="medium"
                    variant="soft"
                    accessibilityLabel={strings.accessibility.copy}
                    onPress={handleCopy}
                  />
                  {/* Ngôn ngữ đích không có giọng đọc → chú thích nhỏ, không có nút Đọc to */}
                  {!ttsSupported && (
                    <ThemedText
                      style={[
                        styles.ttsNote,
                        { color: colors.textSecondary, marginLeft: s(12) },
                      ]}
                    >
                      {strings.home.ttsUnsupported}
                    </ThemedText>
                  )}
                </View>

                {/* Lỗi TTS */}
                {ttsError !== null && (
                  <ThemedText
                    style={[styles.ttsError, { color: colors.danger, marginTop: vs(8) }]}
                  >
                    {ttsError}
                  </ThemedText>
                )}
              </View>
            )}

            {/* THẺ LỖI — chỉ hiện khi phase === 'error' */}
            {phase === 'error' && (
              <View
                style={{ marginTop: vs(14) }}
                onLayout={(e) => {
                  errorCardYRef.current = e.nativeEvent.layout.y;
                }}
              >
                <ErrorCard
                  title={strings.error.translateTitle}
                  message={translateError ?? strings.error.generic}
                  onRetry={translate}
                />
              </View>
            )}

            {/* LINK / THẺ NGỮ CẢNH — ẩn khi đang lỗi */}
            {phase !== 'error' && (!contextOpen ? (
              // A) Link "Thêm ngữ cảnh" / "Ngữ cảnh đã thêm"
              <Pressable
                onPress={handleToggleContext}
                accessibilityRole="button"
                accessibilityLabel={
                  hasContext
                    ? `${strings.home.contextAdded}: ${contextSummary}`
                    : strings.home.addContext
                }
                style={({ pressed }) => [
                  styles.contextLink,
                  { marginTop: vs(22), opacity: pressed ? 0.7 : 1 },
                ]}
              >
                <Ionicons
                  name={hasContext ? 'checkmark-circle' : 'add'}
                  size={ms(20)}
                  color={colors.primary}
                />
                <ThemedText
                  style={[styles.contextLinkBold, { color: colors.primary, marginLeft: s(8) }]}
                >
                  {hasContext ? strings.home.contextAdded : strings.home.addContext}
                </ThemedText>
                <ThemedText
                  style={[styles.contextLinkMuted, { color: colors.textSecondary }]}
                >
                  {hasContext ? ` ${contextSummary}` : ` ${strings.home.contextOptional}`}
                </ThemedText>
              </Pressable>
            ) : (
              // B) Thẻ ngữ cảnh mở
              <View
                style={[
                  styles.contextCard,
                  {
                    backgroundColor: colors.surface,
                    borderColor: colors.border,
                    marginTop: vs(14),
                  },
                ]}
              >
                {/* Tiêu đề — bấm để đóng */}
                <Pressable
                  onPress={handleToggleContext}
                  accessibilityRole="button"
                  accessibilityLabel={strings.context.closeLabel}
                  style={({ pressed }) => [
                    styles.contextCardHeader,
                    { opacity: pressed ? 0.7 : 1 },
                  ]}
                >
                  <View style={styles.contextCardTitleRow}>
                    <ThemedText style={[styles.contextCardTitle, { color: colors.textPrimary }]}>
                      {strings.context.title}
                    </ThemedText>
                    <ThemedText style={[styles.contextCardOptional, { color: colors.textSecondary }]}>
                      {` ${strings.context.optional}`}
                    </ThemedText>
                  </View>
                  <Ionicons name="chevron-up" size={ms(22)} color={colors.textSecondary} />
                </Pressable>

                {/* Ô ghi chú */}
                <TextInput
                  multiline
                  value={contextNote}
                  onChangeText={setContextNote}
                  placeholder={strings.context.notePlaceholder}
                  placeholderTextColor={colors.placeholder}
                  maxLength={strings.context.noteMax}
                  scrollEnabled
                  maxFontSizeMultiplier={1.2}
                  style={[
                    styles.contextNoteInput,
                    {
                      marginTop: vs(14),
                      backgroundColor: colors.inputBg,
                      borderColor: colors.border,
                      color: colors.textPrimary,
                      fontSize: ms(17),
                      minHeight: vs(62),
                    },
                  ]}
                />

                {/* Bộ đếm ký tự — căn phải */}
                <ThemedText
                  style={[
                    styles.contextCounter,
                    { marginTop: vs(6), color: colors.textSecondary },
                  ]}
                >
                  {`${contextNote.length}/${strings.context.noteMax}`}
                </ThemedText>

                {/* Lưới 4 ToneChip */}
                <View style={[styles.toneGrid, { marginTop: vs(14) }]}>
                  {TONES.map((tone) => (
                    <ToneChip
                      key={tone.id}
                      label={tone.label}
                      checked={tones.includes(tone.id)}
                      onToggle={() => toggleTone(tone.id)}
                    />
                  ))}
                </View>
              </View>
            ))}

          </View>
        </ScrollView>

        {/* ── NÚT DỊCH CỐ ĐỊNH ── chỉ hiện khi phase idle/translating */}
        {showTranslateBar && (
          <View
            style={[
              styles.translateBar,
              {
                paddingBottom: vs(17) + insets.bottom,
                backgroundColor: colors.background,
              },
            ]}
          >
            <View style={styles.contentWrapper}>
              <PrimaryButton
                label={phase === 'translating' ? strings.home.translating : strings.home.translate}
                onPress={handleTranslate}
                disabled={!hasText}
                loading={phase === 'translating'}
              />
            </View>
          </View>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  kav: {
    flex: 1,
  },
  inner: {
    flex: 1,
  },

  // Phần cố định trên (header + hàng ngôn ngữ); không cuộn
  topFixed: {
    // backgroundColor kế thừa từ kav (KeyboardAvoidingView)
  },

  // Wrapper căn giữa nội dung (tablet không bị giãn)
  contentWrapper: {
    width: '100%',
    maxWidth: MAX_CONTENT_WIDTH,
    alignSelf: 'center',
    paddingHorizontal: s(21),
  },

  // ── Header ──
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    minHeight: s(46),
    paddingTop: vs(8),
    marginTop: vs(8),
  },

  // ── Hàng ngôn ngữ ──
  languageRow: {
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: vs(59),
  },
  arrowWrap: {
    width: s(38),
    alignItems: 'center',
    justifyContent: 'center',
  },

  // ── Scroll ──
  scrollArea: {
    flex: 1,
  },
  scrollContent: {
    paddingTop: vs(14),
    paddingBottom: vs(24),
  },

  // ── Ô nhập ──
  inputCard: {
    borderRadius: s(24),
    borderWidth: 1,
    maxHeight: vs(330),
    overflow: 'hidden',
  },
  textInput: {
    paddingHorizontal: s(22),
    paddingTop: vs(20),
    paddingBottom: vs(8),
    flexShrink: 1,
  },
  clearButton: {
    position: 'absolute',
    width: s(36),
    height: s(36),
    alignItems: 'center',
    justifyContent: 'center',
  },
  inputActions: {
    position: 'absolute',
    flexDirection: 'row',
    alignItems: 'center',
  },

  // ── Dòng thông báo nhỏ dưới ô nhập ──
  inputHint: {
    fontSize: ms(14),
    lineHeight: ms(20),
    fontWeight: '400',
    paddingHorizontal: s(4),
  },

  // ── Link ngữ cảnh ──
  contextLink: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingLeft: s(8),
  },
  contextLinkBold: {
    fontSize: ms(16),
    fontWeight: '700',
  },
  contextLinkMuted: {
    fontSize: ms(16),
    fontWeight: '400',
    flexShrink: 1,
  },

  // ── Thẻ ngữ cảnh ──
  contextCard: {
    borderRadius: s(24),
    borderWidth: 1,
    padding: s(22),
  },
  contextCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  contextCardTitleRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    flex: 1,
    marginRight: s(8),
  },
  contextCardTitle: {
    fontSize: ms(17),
    fontWeight: '700',
  },
  contextCardOptional: {
    fontSize: ms(17),
    fontWeight: '400',
  },
  contextNoteInput: {
    borderWidth: 1,
    borderRadius: s(15),
    padding: s(14),
    textAlignVertical: 'top',
  },
  contextCounter: {
    fontSize: ms(14),
    textAlign: 'right',
  },
  toneGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: s(9),
  },

  // ── Thẻ kết quả ──
  resultCard: {
    borderRadius: s(24),
    borderWidth: 1,
    padding: s(22),
  },
  resultLang: {
    fontSize: ms(13),
    fontWeight: '700',
  },
  resultText: {
    // padding ngang lẻ để chữ không chạm viền card (card đã padding s(22))
    paddingLeft: 0,
    paddingRight: 0,
  },
  resultActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  ttsError: {
    fontSize: ms(14),
    fontWeight: '400',
  },
  ttsNote: {
    fontSize: ms(13),
    fontWeight: '400',
    flexShrink: 1,
  },

  // ── Thanh nút Dịch cố định ──
  translateBar: {
    paddingTop: vs(10),
    // paddingHorizontal do contentWrapper bên trong đảm nhiệm (tránh canh lệch 2 lần)
    // paddingBottom tính động (insets.bottom + vs(17))
  },
});
