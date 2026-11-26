import React from 'react';
import { View, StyleSheet } from 'react-native';
import IconCircleButton from './IconCircleButton';
import ThemedText from '../theme/ThemedText';
import { strings } from '../constants/strings';
import { s } from '../utils/scale';

interface Props {
  title: string;
  onBack: () => void;
}

export default function ScreenHeader({ title, onBack }: Props) {
  return (
    <View style={styles.row}>
      <IconCircleButton
        icon="chevron-back"
        size="small"
        variant="neutral"
        accessibilityLabel={strings.accessibility.back}
        onPress={onBack}
      />
      <ThemedText variant="screenTitle" style={styles.title}>
        {title}
      </ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: s(46),
  },
  title: {
    marginLeft: s(12),
  },
});
