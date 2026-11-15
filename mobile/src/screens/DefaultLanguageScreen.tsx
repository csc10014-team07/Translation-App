import React, { useCallback, useRef, useEffect } from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  ListRenderItemInfo,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { DefaultLanguageScreenProps } from '../navigation/types';
import { useTheme } from '../theme/ThemeProvider';
import ThemedText from '../theme/ThemedText';
import ScreenHeader from '../components/ScreenHeader';
import LanguageRow from '../components/LanguageRow';
import { strings } from '../constants/strings';
import {
  TARGET_LANGUAGES,
  TargetLanguageCode,
} from '../constants/languages';
import {
  useSettingsStore,
} from '../store/settingsStore';
import { s, vs, ms, MAX_CONTENT_WIDTH } from '../utils/scale';

type LanguageItem = (typeof TARGET_LANGUAGES)[number];

/** Thời gian giữ màn để người dùng thấy dấu ✓ chuyển trước khi quay lại. */
const GO_BACK_DELAY_MS = 250;

export default function DefaultLanguageScreen({
  navigation,
}: DefaultLanguageScreenProps) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const defaultTargetLang = useSettingsStore((st) => st.defaultTargetLang);
  const setDefaultTargetLang = useSettingsStore((st) => st.setDefaultTargetLang);

  const goBackTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Dọn timeout khi unmount
  useEffect(() => {
    return () => {
      if (goBackTimeoutRef.current) clearTimeout(goBackTimeoutRef.current);
    };
  }, []);

  const handleSelect = useCallback(
    (code: TargetLanguageCode) => {
      // Chỉ đổi mặc định cho lần mở app sau — KHÔNG đổi targetLanguage đang dùng.
      setDefaultTargetLang(code);
      // Giữ màn một nhịp để thấy dấu ✓, rồi quay lại.
      if (goBackTimeoutRef.current) clearTimeout(goBackTimeoutRef.current);
      goBackTimeoutRef.current = setTimeout(() => {
        navigation.goBack();
      }, GO_BACK_DELAY_MS);
    },
    [setDefaultTargetLang, navigation],
  );

  const renderItem = useCallback(
    ({ item }: ListRenderItemInfo<LanguageItem>) => (
      <LanguageRow
        label={item.label}
        selected={item.code === defaultTargetLang}
        onPress={() => handleSelect(item.code as TargetLanguageCode)}
      />
    ),
    [defaultTargetLang, handleSelect],
  );

  return (
    <View style={[styles.safe, { backgroundColor: colors.background }]}>
      <View style={styles.contentWrapper}>
        {/* ── HEADER ── */}
        <View style={{ paddingTop: insets.top + vs(8) }}>
          <ScreenHeader
            title={strings.defaultLanguage.title}
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
          {strings.defaultLanguage.description}
        </ThemedText>

        {/* ── NHÃN SECTION ── */}
        <ThemedText
          style={[
            styles.sectionLabel,
            { color: colors.textSecondary, marginTop: vs(22) },
          ]}
        >
          {strings.defaultLanguage.section}
        </ThemedText>

        {/* ── DANH SÁCH ── */}
        <FlatList
          data={TARGET_LANGUAGES}
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
