import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { s, vs } from '../utils/scale';

interface Props {
  color: string;
  /** Khoảng cách từ mép trên màn hình (dp, đã qua vs()). */
  top?: number;
  /** Khoảng cách từ mép dưới màn hình (dp, đã qua vs()). */
  bottom?: number;
  /** Khoảng cách ngang từ mép trái/phải (dp). */
  horizontalInset?: number;
  /**
   * Cộng thêm px thô (KHÔNG scale) vào mép trên/dưới — dùng cho safe area
   * inset để khung không đè lên tai thỏ (top) hay thanh điều hướng (bottom).
   */
  topExtra?: number;
  bottomExtra?: number;
  /**
   * Ghi đè mép dưới bằng px thô (đã bao gồm inset). Khi truyền giá trị này,
   * `bottom` + `bottomExtra` bị bỏ qua — dùng để khung bám đúng chiều cao
   * thanh/panel dưới (đo bằng onLayout), tránh chồng trên máy thấp.
   */
  bottomOverride?: number;
}

const CORNER = 38; // dp
const RADIUS = 20; // dp
const BORDER = 3; // px cố định

export default function CornerFrame({
  color,
  top = 93,
  bottom = 165,
  horizontalInset = 25,
  topExtra = 0,
  bottomExtra = 0,
  bottomOverride,
}: Props) {
  const cornerSize = s(CORNER);
  const cornerRadius = s(RADIUS);

  const base: ViewStyle = {
    position: 'absolute',
    width: cornerSize,
    height: cornerSize,
    borderColor: color,
  };

  return (
    <View
      pointerEvents="none"
      style={[
        StyleSheet.absoluteFill,
        {
          left: s(horizontalInset),
          right: s(horizontalInset),
          top: vs(top) + topExtra,
          bottom:
            bottomOverride !== undefined
              ? bottomOverride
              : vs(bottom) + bottomExtra,
        },
      ]}
    >
      {/* Trên-trái */}
      <View
        style={[
          base,
          {
            top: 0,
            left: 0,
            borderTopWidth: BORDER,
            borderLeftWidth: BORDER,
            borderTopLeftRadius: cornerRadius,
          },
        ]}
      />

      {/* Trên-phải */}
      <View
        style={[
          base,
          {
            top: 0,
            right: 0,
            borderTopWidth: BORDER,
            borderRightWidth: BORDER,
            borderTopRightRadius: cornerRadius,
          },
        ]}
      />

      {/* Dưới-trái */}
      <View
        style={[
          base,
          {
            bottom: 0,
            left: 0,
            borderBottomWidth: BORDER,
            borderLeftWidth: BORDER,
            borderBottomLeftRadius: cornerRadius,
          },
        ]}
      />

      {/* Dưới-phải */}
      <View
        style={[
          base,
          {
            bottom: 0,
            right: 0,
            borderBottomWidth: BORDER,
            borderRightWidth: BORDER,
            borderBottomRightRadius: cornerRadius,
          },
        ]}
      />
    </View>
  );
}
