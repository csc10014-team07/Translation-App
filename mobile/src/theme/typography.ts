/**
 * Tipography Translation-App (font Be Vietnam Pro).
 * Tất cả cỡ chữ và lineHeight đều dùng ms() để co giãn vừa phải theo màn hình.
 */

import { ms } from '../utils/scale';

export const FONT_REGULAR = 'BeVietnamPro_400Regular';
export const FONT_MEDIUM = 'BeVietnamPro_500Medium';
export const FONT_SEMIBOLD = 'BeVietnamPro_600SemiBold';
export const FONT_BOLD = 'BeVietnamPro_700Bold';

interface TextStyle {
  fontFamily: string;
  fontSize: number;
  fontWeight: '400' | '500' | '600' | '700';
  lineHeight?: number;
}

export const typography: Record<string, TextStyle> = {
  title: {
    fontFamily: FONT_BOLD,
    fontSize: ms(26),
    fontWeight: '700',
  },
  screenTitle: {
    fontFamily: FONT_BOLD,
    fontSize: ms(28),
    fontWeight: '700',
  },
  bodyLarge: {
    fontFamily: FONT_MEDIUM,
    fontSize: ms(24),
    fontWeight: '500',
    lineHeight: ms(34),
  },
  result: {
    fontFamily: FONT_SEMIBOLD,
    fontSize: ms(25),
    fontWeight: '600',
    lineHeight: ms(38),
  },
  button: {
    fontFamily: FONT_BOLD,
    fontSize: ms(19),
    fontWeight: '700',
  },
  itemTitle: {
    fontFamily: FONT_BOLD,
    fontSize: ms(19),
    fontWeight: '700',
  },
  cardTitle: {
    fontFamily: FONT_BOLD,
    fontSize: ms(17),
    fontWeight: '700',
  },
  label: {
    fontFamily: FONT_MEDIUM,
    fontSize: ms(12),
    fontWeight: '500',
  },
  value: {
    fontFamily: FONT_BOLD,
    fontSize: ms(17),
    fontWeight: '700',
  },
  body: {
    fontFamily: FONT_REGULAR,
    fontSize: ms(15),
    fontWeight: '400',
  },
  caption: {
    fontFamily: FONT_REGULAR,
    fontSize: ms(14),
    fontWeight: '400',
  },
};

export type TypographyVariant = keyof typeof typography;
