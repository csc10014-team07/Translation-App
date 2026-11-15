import React, { useCallback, useRef, useEffect } from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  ListRenderItemInfo,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { SourceLanguageScreenProps } from '../navigation/types';
import { useTheme } from '../theme/ThemeProvider';
import ThemedText from '../theme/ThemedText';
import ScreenHeader from '../components/ScreenHeader';
import LanguageRow from '../components/LanguageRow';
import { strings } from '../constants/strings';
import {
  SOURCE_LANGUAGES,
  getSourceFullLabel,
  Language,
} from '../constants/languages';
import { useTranslationStore } from '../store/translationStore';
import { s, vs, ms, MAX_CONTENT_WIDTH } from '../utils/scale';

type LanguageItem = Language;

/** Thời gian giữ màn để người dùng thấy dấu ✓ chuyển trước khi quay lại. */
const GO_BACK_DELAY_MS = 250;

export default function SourceLanguageScreen({
  navigation,
}: SourceLanguageScreenProps) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const inputLanguage = useTranslationStore((st) => st.inputLanguage);
  const setSourceLang = useTranslationStore((st) => st.setSourceLang);

  const goBackTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Dọn timeout khi unmount
  useEffect(() => {
    return () => {
      if (goBackTimeoutRef.current) clearTimeout(goBackTimeoutRef.current);
    };
  }, []);

  const handleSelect = useCallback(
    (code: string) => {
      // Store tự lưu mặc định và tự hoán đổi đích nếu trùng nguồn.
      setSourceLang(code);
      // Giữ màn một nhịp để thấy dấu ✓ chuyển, rồi quay lại.
      if (goBackTimeoutRef.current) clearTimeout(goBackTimeoutRef.current);
      goBackTimeoutRef.current = setTimeout(() => {
        navigation.goBack();
      }, GO_BACK_DELAY_MS);
    },
    [setSourceLang, navigation],
  );

  const renderItem = useCallback(
    ({ item }: ListRenderItemInfo<LanguageItem>) => (
      <LanguageRow
        label={getSourceFullLabel(item.code)}
        selected={item.code === inputLanguage}
        onPress={() => handleSelect(item.code)}
      />
    ),
    [inputLanguage, handleSelect],
  );

  return (
    <View style={[styles.safe, { backgroundColor: colors.background }]}>
      <View style={styles.contentWrapper}>
        {/* ── HEADER ── */}
        <View style={{ paddingTop: insets.top + vs(8) }}>
          <ScreenHeader
            title={strings.sourceLanguage.title}
            onBack={() => navigation.goBack()}
          />
        </View>

        {/* ── MÔ TẢ ── */}
        <ThemedText
          style={[
            styles.description,
            { color: colors.textSecondary, marginTop: vs(18) },
          ]}
        >
          {strings.sourceLanguage.description}
        </ThemedText>

        {/* ── NHÃN SECTION ── */}
        <ThemedText
          style={[
            styles.sectionLabel,
            { color: colors.textSecondary, marginTop: vs(22) },
          ]}
        >
          {strings.sourceLanguage.section}
        </ThemedText>

        {/* ── DANH SÁCH ── */}
        <FlatList
          data={SOURCE_LANGUAGES}
          keyExtractor={(item) => item.code}
          renderItem={renderItem}
          style={{ marginTop: vs(10) }}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={{
            paddingBottom: vs(24) + insets.bottom,
          }}
          ItemSeparatorComponent={() => <View style={{ height: vs(3) }} />}
        />
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

  // ── Mô tả ──
  description: {
    fontSize: ms(15),
    lineHeight: ms(22),
    fontWeight: '400',
    paddingLeft: s(19),
  },

  // ── Nhãn section ──
  sectionLabel: {
    fontSize: ms(14),
    fontWeight: '700',
    paddingLeft: s(19),
  },
});
