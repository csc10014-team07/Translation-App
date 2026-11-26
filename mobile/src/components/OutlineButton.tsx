import React from 'react';
import { Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeProvider';
import { cameraColors } from '../theme/colors';
import ThemedText from '../theme/ThemedText';
import { s, vs, ms } from '../utils/scale';

type Tone = 'default' | 'danger' | 'dark';
type Size = 'md' | 'lg';

interface Props {
  label: string;
  onPress: () => void;
  iconLeft?: keyof typeof Ionicons.glyphMap;
  tone?: Tone;
  fullWidth?: boolean;
  size?: Size;
  accessibilityLabel?: string;
  disabled?: boolean;
}

export default function OutlineButton({
  label,
  onPress,
  iconLeft,
  tone = 'default',
  fullWidth = true,
  size = 'md',
  accessibilityLabel,
  disabled = false,
}: Props) {
  const { colors } = useTheme();

  const isLg = size === 'lg';
  const minHeight = isLg ? vs(59) : vs(48);
  const radius = isLg ? s(22) : s(14);

  let bg: string;
  let fg: string;
  let border: string;

  switch (tone) {
    case 'danger':
      bg = colors.surface;
      fg = colors.danger;
      border = colors.danger;
      break;
    case 'dark':
      // Nút "Chụp lại" trên nền camera tối: nền trắng, chữ đậm tối.
      bg = cameraColors.buttonSurface;
      fg = cameraColors.buttonText;
      border = 'transparent';
      break;
    default:
      bg = colors.surface;
      fg = colors.textPrimary;
      border = colors.borderStrong;
      break;
  }

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.button,
        !fullWidth && styles.notFullWidth,
        {
          minHeight,
          borderRadius: radius,
          borderWidth: border === 'transparent' ? 0 : 1,
          borderColor: border,
          backgroundColor: bg,
          opacity: pressed ? 0.85 : disabled ? 0.5 : 1,
        },
      ]}
    >
      {iconLeft ? (
        <Ionicons name={iconLeft} size={ms(22)} color={fg} style={styles.icon} />
      ) : null}
      <ThemedText variant="body" style={{ color: fg, fontWeight: '700', fontSize: ms(17) }}>
        {label}
      </ThemedText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  notFullWidth: {
    alignSelf: 'flex-start',
    paddingHorizontal: s(22),
  },
  icon: {
    marginRight: s(8),
  },
});
