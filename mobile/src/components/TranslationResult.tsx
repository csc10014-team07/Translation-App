import React, { useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Clipboard,
  useColorScheme,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface Props {
  translatedText: string;
  sourceLanguage: string;
  targetLanguage: string;
}

const PRIMARY = '#4F46E5';

export default function TranslationResult({
  translatedText,
  sourceLanguage,
  targetLanguage,
}: Props) {
  const scheme = useColorScheme();
  const isDark = scheme === 'dark';

  const handleCopy = useCallback(() => {
    Clipboard.setString(translatedText);
  }, [translatedText]);

  if (!translatedText) return null;

  return (
    <View style={[styles.card, isDark && styles.cardDark]}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.langBadgeRow}>
          {sourceLanguage ? (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{sourceLanguage.toUpperCase()}</Text>
            </View>
          ) : null}
          {sourceLanguage ? (
            <Ionicons name="arrow-forward" size={14} color="#888" />
          ) : null}
          <View style={[styles.badge, styles.badgeTarget]}>
            <Text style={[styles.badgeText, styles.badgeTextTarget]}>
              {targetLanguage.toUpperCase()}
            </Text>
          </View>
        </View>
        <TouchableOpacity
          style={styles.copyButton}
          onPress={handleCopy}
          accessibilityLabel="Copy translated text"
        >
          <Ionicons name="copy-outline" size={18} color={PRIMARY} />
          <Text style={styles.copyLabel}>Copy</Text>
        </TouchableOpacity>
      </View>

      {/* Translation text */}
      <Text
        style={[styles.translatedText, isDark && styles.translatedTextDark]}
        selectable
      >
        {translatedText}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#e0e0f0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 2,
  },
  cardDark: {
    backgroundColor: '#1a1a2e',
    borderColor: '#2a2a3e',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  langBadgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  badge: {
    backgroundColor: '#e8e8f0',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  badgeTarget: {
    backgroundColor: PRIMARY,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#555',
  },
  badgeTextTarget: {
    color: '#fff',
  },
  copyButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    padding: 4,
  },
  copyLabel: {
    fontSize: 14,
    color: PRIMARY,
    fontWeight: '500',
  },
  translatedText: {
    fontSize: 16,
    lineHeight: 24,
    color: '#222',
  },
  translatedTextDark: {
    color: '#eee',
  },
});
