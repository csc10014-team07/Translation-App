import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  useColorScheme,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

type InputMode = 'text' | 'voice' | 'image';

interface Props {
  mode: InputMode;
  onChangeMode: (mode: InputMode) => void;
}

interface Tab {
  key: InputMode;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
}

const TABS: Tab[] = [
  { key: 'text', label: 'Text', icon: 'create-outline' },
  { key: 'voice', label: 'Voice', icon: 'mic-outline' },
  { key: 'image', label: 'Image', icon: 'image-outline' },
];

const PRIMARY = '#4F46E5';

export default function InputModeSelector({ mode, onChangeMode }: Props) {
  const scheme = useColorScheme();
  const isDark = scheme === 'dark';

  return (
    <View style={[styles.container, isDark && styles.containerDark]}>
      {TABS.map((tab) => {
        const active = tab.key === mode;
        return (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tab, active && styles.tabActive]}
            onPress={() => onChangeMode(tab.key)}
            activeOpacity={0.75}
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            accessibilityLabel={`${tab.label} input mode`}
          >
            <Ionicons
              name={active ? (tab.icon.replace('-outline', '') as keyof typeof Ionicons.glyphMap) : tab.icon}
              size={20}
              color={active ? '#fff' : isDark ? '#aaa' : '#666'}
            />
            <Text style={[styles.label, active && styles.labelActive, isDark && !active && styles.labelDark]}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    backgroundColor: '#f0f0f5',
    borderRadius: 12,
    padding: 4,
    marginBottom: 16,
  },
  containerDark: {
    backgroundColor: '#1e1e2e',
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: 9,
    gap: 6,
  },
  tabActive: {
    backgroundColor: PRIMARY,
    shadowColor: PRIMARY,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.35,
    shadowRadius: 4,
    elevation: 3,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666',
  },
  labelDark: {
    color: '#aaa',
  },
  labelActive: {
    color: '#fff',
  },
});
