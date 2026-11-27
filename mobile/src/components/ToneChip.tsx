import React from 'react';
import { Pressable, View, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeProvider';
import ThemedText from '../theme/ThemedText';
import { s, vs, ms } from '../utils/scale';

interface Props {
  label: string;
  checked: boolean;
  onToggle: () => void;
}

export default function ToneChip({ label, checked, onToggle }: Props) {
  const { colors } = useTheme();

  return (
    <Pressable
      onPress={onToggle}
      accessibilityRole="checkbox"
      accessibilityState={{ checked }}
      accessibilityLabel={label}
      style={({ pressed }) => [
        styles.chip,
        {
          minHeight: vs(47),
          borderRadius: vs(47) / 2,
          paddingHorizontal: s(16),
          backgroundColor: checked ? colors.primarySoft : colors.surface,
          borderWidth: checked ? 1.5 : 1,
          borderColor: checked ? colors.primary : colors.borderStrong,
          opacity: pressed ? 0.85 : 1,
        },
      ]}
    >
      <View
        style={[
          styles.checkbox,
          {
            width: s(18),
            height: s(18),
            borderRadius: s(3),
            borderWidth: 1.5,
            borderColor: checked ? colors.primary : colors.textSecondary,
            backgroundColor: checked ? colors.primary : 'transparent',
          },
        ]}
      >
        {checked ? (
          <Ionicons name="checkmark" size={ms(13)} color={colors.onPrimary} />
        ) : null}
      </View>

      <ThemedText
        variant="body"
        style={{
          fontSize: ms(17),
          fontWeight: checked ? '700' : '500',
          color: checked ? colors.primaryDark : colors.textPrimary,
          marginLeft: s(12),
        }}
      >
        {label}
      </ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
  },
  checkbox: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
