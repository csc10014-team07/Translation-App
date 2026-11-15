import React from 'react';
import { View, Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeProvider';
import ThemedText from '../theme/ThemedText';
import { s, vs, ms } from '../utils/scale';

interface Props {
  /** Nhãn ngôn ngữ hiển thị (label đầy đủ). */
  label: string;
  /** Hàng này có đang được chọn không. */
  selected: boolean;
  onPress: () => void;
}

/**
 * Hàng ngôn ngữ dùng chung cho màn "Dịch sang" và "Ngôn ngữ mặc định".
 * - Đang chọn: nền primarySoftStrong + icon checkmark.
 * - Chưa chọn: nền trong suốt, chữ vẫn thụt vào cùng vị trí (chừa ô icon).
 */
export default function LanguageRow({ label, selected, onPress }: Props) {
  const { colors } = useTheme();

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="radio"
      accessibilityState={{ selected }}
      accessibilityLabel={label}
      style={({ pressed }) => [
        styles.row,
        {
          backgroundColor: selected ? colors.primarySoftStrong : 'transparent',
          opacity: pressed ? 0.7 : 1,
        },
      ]}
    >
      {/* Ô icon — chừa chỗ cố định để chữ hàng chưa chọn thẳng hàng */}
      <View style={styles.iconSlot}>
        {selected && (
          <Ionicons name="checkmark" size={ms(24)} color={colors.primaryDark} />
        )}
      </View>

      <ThemedText
        style={[
          selected ? styles.labelSelected : styles.label,
          { color: colors.textPrimary },
        ]}
        numberOfLines={1}
      >
        {label}
      </ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    minHeight: vs(59),
    borderRadius: vs(59) / 2,
    flexDirection: 'row',
    alignItems: 'center',
  },
  iconSlot: {
    width: s(36),
    marginLeft: s(18),
    alignItems: 'center',
    justifyContent: 'center',
  },
  labelSelected: {
    fontSize: ms(19),
    fontWeight: '700',
    marginLeft: s(12),
  },
  label: {
    fontSize: ms(19),
    fontWeight: '500',
    marginLeft: s(12),
  },
});
