import React from 'react';
import { Pressable, ActivityIndicator, StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeProvider';
import ThemedText from '../theme/ThemedText';
import { s, vs, ms } from '../utils/scale';

type Variant = 'primary' | 'pill';

interface Props {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  iconLeft?: keyof typeof Ionicons.glyphMap;
  variant?: Variant;
  accessibilityLabel?: string;
}

export default function PrimaryButton({
  label,
  onPress,
  disabled = false,
  loading = false,
  iconLeft,
  variant = 'primary',
  accessibilityLabel,
}: Props) {
  const { colors } = useTheme();

  const isDisabled = disabled || loading;

  if (variant === 'pill') {
    const pillBg = isDisabled ? colors.disabledBg : colors.primary;
    const pillFg = isDisabled ? colors.disabledText : colors.onPrimary;

    return (
      <Pressable
        onPress={onPress}
        disabled={isDisabled}
        accessibilityLabel={accessibilityLabel ?? label}
        accessibilityRole="button"
        style={({ pressed }) => [
          styles.pill,
          {
            minHeight: vs(50),
            paddingHorizontal: s(22),
            borderRadius: vs(25),
            backgroundColor: pillBg,
            opacity: pressed ? 0.85 : 1,
          },
        ]}
      >
        {loading ? (
          <ActivityIndicator color={pillFg} size="small" />
        ) : iconLeft ? (
          <Ionicons name={iconLeft} size={ms(22)} color={pillFg} />
        ) : null}
        <ThemedText
          variant="body"
          style={{
            color: pillFg,
            fontSize: ms(17),
            fontWeight: '700',
            marginLeft: iconLeft || loading ? s(8) : 0,
          }}
        >
          {label}
        </ThemedText>
      </Pressable>
    );
  }

  // ── variant: primary (full-width) ──
  const bg = isDisabled ? colors.disabledBg : colors.primary;
  const fg = isDisabled ? colors.disabledText : colors.onPrimary;

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.primary,
        {
          minHeight: vs(59),
          borderRadius: s(22),
          backgroundColor: bg,
          opacity: pressed ? 0.85 : 1,
        },
      ]}
    >
      {loading ? (
        <ActivityIndicator color={fg} size="small" style={styles.iconLeft} />
      ) : iconLeft ? (
        <Ionicons
          name={iconLeft}
          size={ms(22)}
          color={fg}
          style={styles.iconLeft}
        />
      ) : null}
      <ThemedText variant="button" style={{ color: fg }}>
        {label}
      </ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  primary: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'flex-start',
  },
  iconLeft: {
    marginRight: s(8),
  },
});
