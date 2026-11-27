// Deprecated: thay bởi giao diện V2 (HomeScreen/TargetLanguageScreen/...). Giữ để tham khảo.
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../theme/ThemeProvider';

interface Props {
  title: string;
}

/**
 * Màn hình TẠM — chỉ hiện tên màn ở giữa để kiểm tra điều hướng.
 * Sẽ bị thay thế bằng giao diện thật ở các bước sau.
 */
export default function PlaceholderScreen({ title }: Props) {
  const { colors } = useTheme();

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Text style={[styles.title, { color: colors.textPrimary }]}>{title}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
  },
});
