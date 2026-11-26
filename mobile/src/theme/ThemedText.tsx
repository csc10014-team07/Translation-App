import React from 'react';
import { Text, TextProps, StyleProp, TextStyle } from 'react-native';
import { useTheme } from './ThemeProvider';
import { typography, TypographyVariant } from './typography';
import { ThemeColors } from './colors';

interface Props extends Omit<TextProps, 'style' | 'color'> {
  variant?: TypographyVariant;
  color?: keyof ThemeColors;
  style?: StyleProp<TextStyle>;
}

export default function ThemedText({
  variant = 'body',
  color = 'textPrimary',
  style,
  children,
  ...rest
}: Props) {
  const { colors } = useTheme();
  const base = typography[variant];

  return (
    <Text
      {...rest}
      style={[
        {
          fontFamily: base.fontFamily,
          fontSize: base.fontSize,
          fontWeight: base.fontWeight,
          lineHeight: base.lineHeight,
          color: colors[color],
        },
        style,
      ]}
      maxFontSizeMultiplier={1.2}
    >
      {children}
    </Text>
  );
}
