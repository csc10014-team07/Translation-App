import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeProvider';
import ThemedText from '../theme/ThemedText';
import OutlineButton from './OutlineButton';
import { strings } from '../constants/strings';
import { s, vs, ms } from '../utils/scale';

interface Props {
  title: string;
  message: string;
  onRetry: () => void;
  retryLabel?: string;
}

export default function ErrorCard({
  title,
  message,
  onRetry,
  retryLabel = strings.error.retry,
}: Props) {
  const { colors } = useTheme();

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: colors.dangerSoft,
          borderColor: colors.dangerBorder,
          borderRadius: s(22),
          padding: s(17),
        },
      ]}
    >
      <View style={styles.header} accessibilityRole="alert">
        <Ionicons
          name="alert-circle-outline"
          size={ms(22)}
          color={colors.danger}
          style={styles.icon}
        />
        <View style={styles.textCol}>
          <ThemedText
            variant="body"
            style={{
              fontWeight: '700',
              fontSize: ms(17),
              color: colors.dangerTitle,
            }}
          >
            {title}
          </ThemedText>
          <ThemedText
            variant="body"
            style={{
              fontSize: ms(15),
              lineHeight: ms(21),
              color: colors.dangerText,
              marginTop: vs(4),
            }}
          >
            {message}
          </ThemedText>
        </View>
      </View>

      <View style={{ marginTop: vs(14) }}>
        <OutlineButton
          label={retryLabel}
          onPress={onRetry}
          iconLeft="refresh"
          tone="danger"
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  icon: {
    marginRight: s(12),
    marginTop: vs(2),
  },
  textCol: {
    flex: 1,
  },
});
