import React from 'react';
import { View, Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeProvider';
import ThemedText from '../theme/ThemedText';
import { s, vs, ms } from '../utils/scale';

interface Props {
  /** Nhãn nhỏ phía trên, ví dụ "Dịch từ" hoặc "Dịch sang". */
  label: string;
  /** Tên ngôn ngữ ngắn hiển thị, ví dụ "Tiếng Việt" / "English". */
  value: string;
  onPress: () => void;
  accessibilityLabel: string;
}

/**
 * Ô ngôn ngữ dùng chung cho hàng ngôn ngữ ở Home ("Dịch từ" / "Dịch sang").
 * - Nền colors.surface, viền 1px colors.border, bo góc s(22).
 * - Bên trái: hai dòng chữ dọc (nhãn 12 + giá trị 17 đậm).
 * - Bên phải: icon chevron-down ms(20) màu textSecondary.
 */
export default function LanguageTile({
  label,
  value,
  onPress,
  accessibilityLabel,
}: Props) {
  const { colors } = useTheme();

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      style={({ pressed }) => [
        styles.tile,
        {
          backgroundColor: colors.surface,
          borderColor: colors.border,
          opacity: pressed ? 0.85 : 1,
        },
      ]}
    >
      <View style={styles.textCol}>
        <ThemedText variant="label" style={{ color: colors.textSecondary }}>
          {label}
        </ThemedText>
        <ThemedText
          variant="value"
          style={{ color: colors.textPrimary }}
          numberOfLines={1}
        >
          {value}
        </ThemedText>
      </View>
      <Ionicons name="chevron-down" size={ms(20)} color={colors.textSecondary} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  tile: {
    flex: 1,
    height: vs(59),
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: s(22),
    paddingHorizontal: s(16),
  },
  textCol: {
    flex: 1,
    gap: vs(2),
  },
});
