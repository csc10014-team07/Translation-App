import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  LayoutAnimation,
  Platform,
  UIManager,
  useColorScheme,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

if (Platform.OS === 'android') {
  UIManager.setLayoutAnimationEnabledExperimental?.(true);
}

interface Props {
  value: string;
  onChangeText: (text: string) => void;
}

const PRIMARY = '#4F46E5';

export default function ContextInput({ value, onChangeText }: Props) {
  const scheme = useColorScheme();
  const isDark = scheme === 'dark';
  const [expanded, setExpanded] = useState(false);

  const toggle = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpanded((prev) => !prev);
  };

  return (
    <View style={[styles.container, isDark && styles.containerDark]}>
      <TouchableOpacity
        style={styles.header}
        onPress={toggle}
        activeOpacity={0.7}
        accessibilityRole="button"
        accessibilityState={{ expanded }}
        accessibilityLabel="Toggle context input"
      >
        <View style={styles.headerLeft}>
          <Ionicons name="information-circle-outline" size={18} color={PRIMARY} />
          <Text style={[styles.headerText, isDark && styles.textDark]}>
            Add context{' '}
            <Text style={styles.optional}>(optional)</Text>
          </Text>
        </View>
        <Ionicons
          name={expanded ? 'chevron-up' : 'chevron-down'}
          size={18}
          color={isDark ? '#aaa' : '#888'}
        />
      </TouchableOpacity>

      {expanded && (
        <TextInput
          style={[styles.input, isDark && styles.inputDark]}
          value={value}
          onChangeText={onChangeText}
          placeholder="e.g., formal business email, casual conversation, medical document..."
          placeholderTextColor={isDark ? '#666' : '#aaa'}
          multiline
          numberOfLines={3}
          textAlignVertical="top"
          accessibilityLabel="Translation context"
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#f8f8ff',
    borderRadius: 12,
    marginBottom: 12,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#e8e8f0',
  },
  containerDark: {
    backgroundColor: '#1a1a2e',
    borderColor: '#2a2a3e',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  headerText: {
    fontSize: 15,
    fontWeight: '500',
    color: '#333',
  },
  textDark: {
    color: '#ddd',
  },
  optional: {
    fontSize: 13,
    color: '#999',
    fontWeight: '400',
  },
  input: {
    marginHorizontal: 14,
    marginBottom: 12,
    padding: 10,
    fontSize: 14,
    color: '#222',
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    minHeight: 80,
  },
  inputDark: {
    backgroundColor: '#12122a',
    borderColor: '#333',
    color: '#eee',
  },
});
