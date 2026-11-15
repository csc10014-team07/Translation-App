import React from 'react';
import { Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeProvider';
import { cameraColors } from '../theme/colors';
import { s, ms } from '../utils/scale';

type SizeName = 'small' | 'medium' | 'large';
type Variant = 'soft' | 'neutral' | 'cameraDark' | 'cameraClose';

interface Props {
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  size?: SizeName;
  variant?: Variant;
  accessibilityLabel: string;
  disabled?: boolean;
  /** Ghi đè màu icon mặc định của variant. */
  iconColor?: string;
}

const DIAMETER: Record<SizeName, number> = {
  small: 46,
  medium: 50,
  large: 54,
};

const ICON_SIZE: Record<SizeName, number> = {
  small: 20,
  medium: 22,
  large: 26,
};

export default function IconCircleButton({
  icon,
  onPress,
  size = 'medium',
  variant = 'soft',
  accessibilityLabel,
  disabled = false,
  iconColor,
}: Props) {
  const { colors } = useTheme();

  const diameter = s(DIAMETER[size]);
  const radius = diameter / 2;
  const iconPx = ms(ICON_SIZE[size]);

  let bg: string;
  let fg: string;

  switch (variant) {
    case 'soft':
      bg = colors.primarySoft;
      fg = colors.primaryDark;
      break;
    case 'neutral':
      bg = colors.iconButtonBg;
      fg = colors.textPrimary;
      break;
    case 'cameraDark':
      bg = cameraColors.circleButton;
      fg = cameraColors.text;
      break;
    case 'cameraClose':
      bg = cameraColors.closeButton;
      fg = cameraColors.text;
      break;
  }

  if (iconColor) {
    fg = iconColor;
  }

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      hitSlop={s(6)}
      accessibilityLabel={accessibilityLabel}
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.base,
        {
          width: diameter,
          height: diameter,
          borderRadius: radius,
          backgroundColor: bg,
          opacity: pressed ? 0.7 : disabled ? 0.4 : 1,
        },
      ]}
    >
      <Ionicons name={icon} size={iconPx} color={fg} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
