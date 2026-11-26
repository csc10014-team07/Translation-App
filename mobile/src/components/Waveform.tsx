import React, { useEffect, useRef } from 'react';
import { View, Animated, StyleSheet } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';
import { s, vs } from '../utils/scale';

interface Props {
  active: boolean;
  /** Mức âm lượng 0–1, tuỳ chọn. */
  level?: number;
}

/** Chiều cao nền (dp) 13 thanh — sóng âm ngẫu nhiên. */
const BAR_HEIGHTS = [20, 34, 52, 30, 56, 36, 18, 46, 30, 52, 28, 38, 16];
/** Thời lượng vòng lặp mỗi thanh (ms), lệch pha cho tự nhiên. */
const DURATIONS = [700, 580, 850, 620, 900, 560, 750, 640, 820, 500, 680, 770, 600];

const BAR_COUNT = BAR_HEIGHTS.length;
const BAR_WIDTH = 6; // dp
const BAR_GAP = 9; // dp

const SCALE_MIN = 0.45;
const SCALE_MAX = 1.0;

export default function Waveform({ active, level }: Props) {
  const { colors } = useTheme();

  const anims = useRef<Animated.Value[]>(
    BAR_HEIGHTS.map(() => new Animated.Value(SCALE_MIN)),
  ).current;

  const loops = useRef<Animated.CompositeAnimation[]>([]);

  useEffect(() => {
    if (active) {
      // Biên độ lớn nhất tuỳ level
      const amp = level !== undefined ? 0.5 + level * 0.5 : SCALE_MAX;
      const peakY = SCALE_MIN + (amp - SCALE_MIN);

      loops.current = anims.map((anim, i) => {
        const duration = DURATIONS[i];
        const loop = Animated.loop(
          Animated.sequence([
            Animated.timing(anim, {
              toValue: peakY,
              duration: duration / 2,
              useNativeDriver: true,
            }),
            Animated.timing(anim, {
              toValue: SCALE_MIN,
              duration: duration / 2,
              useNativeDriver: true,
            }),
          ]),
        );
        loop.start();
        return loop;
      });
    } else {
      // Dừng loop, trả thanh về chiều cao nền
      loops.current.forEach((loop) => loop.stop());
      loops.current = [];
      anims.forEach((anim) => {
        Animated.timing(anim, {
          toValue: SCALE_MIN,
          duration: 250,
          useNativeDriver: true,
        }).start();
      });
    }

    return () => {
      loops.current.forEach((loop) => loop.stop());
      loops.current = [];
    };
  }, [active, level]);

  return (
    <View
      style={styles.container}
      accessible={false}
      importantForAccessibility="no-hide-descendants"
    >
      {anims.map((anim, i) => (
        <Animated.View
          key={i}
          style={[
            styles.bar,
            {
              width: s(BAR_WIDTH),
              height: vs(BAR_HEIGHTS[i]),
              borderRadius: s(BAR_WIDTH) / 2,
              backgroundColor: colors.primary,
              marginLeft: i > 0 ? s(BAR_GAP) : 0,
              opacity: active ? 1 : 0.6,
              transform: [{ scaleY: anim }],
            },
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  bar: {
    // Các thuộc tính động nằm trong inline style
  },
});
