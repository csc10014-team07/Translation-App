import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Modal,
  FlatList,
  StyleSheet,
  SafeAreaView,
  useColorScheme,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { TARGET_LANGUAGES } from '../constants/languages';

interface Props {
  selectedCode: string;
  onSelect: (code: string) => void;
}

const PRIMARY = '#4F46E5';

export default function LanguagePicker({ selectedCode, onSelect }: Props) {
  const scheme = useColorScheme();
  const isDark = scheme === 'dark';
  const [visible, setVisible] = useState(false);

  const selectedLang =
    TARGET_LANGUAGES.find((l) => l.code === selectedCode) ?? TARGET_LANGUAGES[0];

  const handleSelect = (code: string) => {
    onSelect(code);
    setVisible(false);
  };

  return (
    <>
      <TouchableOpacity
        style={[styles.trigger, isDark && styles.triggerDark]}
        onPress={() => setVisible(true)}
        activeOpacity={0.8}
        accessibilityLabel={`Target language: ${selectedLang.name}. Tap to change.`}
        accessibilityRole="button"
      >
        <View style={styles.triggerLeft}>
          <Ionicons name="language" size={20} color={PRIMARY} />
          <Text style={[styles.triggerLabel, isDark && styles.textDark]}>
            Translate to
          </Text>
        </View>
        <View style={styles.triggerRight}>
          <Text style={styles.selectedName}>{selectedLang.name}</Text>
          <Ionicons name="chevron-down" size={16} color={PRIMARY} />
        </View>
      </TouchableOpacity>

      <Modal
        visible={visible}
        animationType="slide"
        transparent
        onRequestClose={() => setVisible(false)}
      >
        <TouchableOpacity
          style={styles.overlay}
          activeOpacity={1}
          onPress={() => setVisible(false)}
        />
        <SafeAreaView
          style={[styles.sheet, isDark && styles.sheetDark]}
        >
          <View style={styles.sheetHeader}>
            <Text style={[styles.sheetTitle, isDark && styles.textDark]}>
              Select Language
            </Text>
            <TouchableOpacity onPress={() => setVisible(false)} accessibilityLabel="Close language picker">
              <Ionicons name="close" size={24} color={isDark ? '#ccc' : '#444'} />
            </TouchableOpacity>
          </View>
          <FlatList
            data={TARGET_LANGUAGES}
            keyExtractor={(item) => item.code}
            renderItem={({ item }) => {
              const active = item.code === selectedCode;
              return (
                <TouchableOpacity
                  style={[styles.row, active && styles.rowActive, isDark && styles.rowDark]}
                  onPress={() => handleSelect(item.code)}
                  accessibilityRole="button"
                  accessibilityState={{ selected: active }}
                >
                  <Text
                    style={[
                      styles.rowText,
                      active && styles.rowTextActive,
                      isDark && styles.textDark,
                    ]}
                  >
                    {item.name}
                  </Text>
                  {active && (
                    <Ionicons name="checkmark" size={20} color={PRIMARY} />
                  )}
                </TouchableOpacity>
              );
            }}
          />
        </SafeAreaView>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  trigger: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#f0f0fa',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  triggerDark: {
    backgroundColor: '#1a1a2e',
    borderColor: '#2a2a3e',
  },
  triggerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  triggerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  triggerLabel: {
    fontSize: 15,
    color: '#444',
    fontWeight: '500',
  },
  selectedName: {
    fontSize: 15,
    fontWeight: '700',
    color: PRIMARY,
  },
  textDark: {
    color: '#ddd',
  },
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  sheet: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '60%',
    paddingBottom: 20,
  },
  sheetDark: {
    backgroundColor: '#1a1a2e',
  },
  sheetHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  sheetTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#222',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#eee',
  },
  rowDark: {
    borderBottomColor: '#2a2a3e',
  },
  rowActive: {
    backgroundColor: '#f0effe',
  },
  rowText: {
    fontSize: 15,
    color: '#333',
  },
  rowTextActive: {
    color: PRIMARY,
    fontWeight: '600',
  },
});
