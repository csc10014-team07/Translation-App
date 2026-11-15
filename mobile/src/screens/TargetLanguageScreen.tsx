import React, { useCallback } from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  ListRenderItemInfo,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { TargetLanguageScreenProps } from '../navigation/types';
import { useTheme } from '../theme/ThemeProvider';
import ThemedText from '../theme/ThemedText';
import ScreenHeader from '../components/ScreenHeader';
import LanguageRow from '../components/LanguageRow';
import { strings } from '../constants/strings';
import { TARGET_LANGUAGES, getTargetFullLabel } from '../constants/languages';
import { useTranslationStore } from '../store/translationStore';
import { s, vs, ms, MAX_CONTENT_WIDTH } from '../utils/scale';

type LanguageItem = (typeof TARGET_LANGUAGES)[number];

export default function TargetLanguageScreen({
  navigation,
}: TargetLanguageScreenProps) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const targetLanguage = useTranslationStore((st) => st.targetLanguage);
  const inputLanguage = useTranslationStore((st) => st.inputLanguage);
  const setTargetLang = useTranslationStore((st) => st.setTargetLang);

  const handleSelect = useCallback(
    (code: string) => {
      setTargetLang(code);
      navigation.goBack();
    },
    [setTargetLang, navigation],
  );

  const renderItem = useCallback(
    ({ item }: ListRenderItemInfo<LanguageItem>) => (
      <LanguageRow
        label={getTargetFullLabel(item.code)}
        selected={item.code === targetLanguage}
        // Không ẩn hàng trùng nguồn: chọn nó sẽ hoán đổi hai bên.
        subtitle={
          item.code === inputLanguage ? strings.targetLanguage.isSourceHint : undefined
        }
        onPress={() => handleSelect(item.code)}
      />
    ),
    [targetLanguage, inputLanguage, handleSelect],
  );

  return (
    <View style={[styles.safe, { backgroundColor: colors.background }]}>
      <View style={styles.contentWrapper}>
        {/* ── HEADER ── */}
        <View style={{ paddingTop: insets.top + vs(8) }}>
          <ScreenHeader
            title={strings.targetLanguage.title}
            onBack={() => navigation.goBack()}
          />
        </View>

        {/* ── NHÃN SECTION ── */}
        <ThemedText
          style={[
            styles.sectionLabel,
            { color: colors.textSecondary, marginTop: vs(24) },
          ]}
        >
          {strings.targetLanguage.available}
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

  // ── Nhãn section ──
  sectionLabel: {
    fontSize: ms(14),
    fontWeight: '700',
    paddingLeft: s(19),
  },
});
