import React, { useCallback, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  AppState,
  useColorScheme,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTranslationStore } from '../store/translationStore';
import { isLiveAudioSupported } from '../services/liveAudio';
import InputModeSelector from '../components/InputModeSelector';
import VoiceRecorder from '../components/VoiceRecorder';
import ImagePickerButton from '../components/ImagePickerButton';
import ContextInput from '../components/ContextInput';
import LanguagePicker from '../components/LanguagePicker';
import TranslationResult from '../components/TranslationResult';
import VoiceCloningPanel from '../components/VoiceCloningPanel';

const PRIMARY = '#4F46E5';

export default function TranslationScreen() {
  const scheme = useColorScheme();
  const isDark = scheme === 'dark';

  const {
    inputMode,
    vietnameseText,
    context,
    targetLanguage,
    translatedText,
    sourceLanguage,
    synthesizedAudioUri,
    isTranscribing,
    isOcrProcessing,
    isTranslating,
    isSynthesizing,
    isStreaming,
    error,
    setInputMode,
    setVietnameseText,
    setContext,
    setTargetLanguage,
    transcribeAudio,
    processImage,
    translate,
    setReferenceAudio,
    synthesize,
    startStreaming,
    stopStreaming,
    clearError,
  } = useTranslationStore();

  const handleVoiceRecorded = useCallback(
    (uri: string) => {
      transcribeAudio(uri);
    },
    [transcribeAudio],
  );

  const handleImageSelected = useCallback(
    (uri: string) => {
      processImage(uri);
    },
    [processImage],
  );

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (nextState) => {
      if (nextState !== 'active') stopStreaming();
    });
    return () => {
      subscription.remove();
      stopStreaming();
    };
  }, [stopStreaming]);

  const isProcessingInput = isTranscribing || isOcrProcessing;

  return (
    <ScrollView
      style={[styles.screen, isDark && styles.screenDark]}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
    >
      {/* Error Banner */}
      {error ? (
        <TouchableOpacity
          style={styles.errorBanner}
          onPress={clearError}
          accessibilityLabel="Dismiss error"
        >
          <Ionicons name="warning" size={16} color="#fff" />
          <Text style={styles.errorText} numberOfLines={3}>
            {error}
          </Text>
          <Ionicons name="close" size={16} color="#fff" />
        </TouchableOpacity>
      ) : null}

      {/* ── Input Mode Selector ── */}
      <InputModeSelector mode={inputMode} onChangeMode={setInputMode} />

      {/* ── Input Area ── */}
      {inputMode === 'text' && (
        <TextInput
          style={[styles.textInput, isDark && styles.textInputDark]}
          value={vietnameseText}
          onChangeText={setVietnameseText}
          placeholder="Type Vietnamese text here…"
          placeholderTextColor={isDark ? '#555' : '#bbb'}
          multiline
          numberOfLines={4}
          textAlignVertical="top"
          accessibilityLabel="Vietnamese text input"
        />
      )}

      {inputMode === 'voice' && (
        <>
          <View style={styles.streamControlRow}>
            <TouchableOpacity
              style={[
                styles.streamButton,
                isStreaming ? styles.streamButtonActive : styles.streamButtonInactive,
              ]}
              onPress={() => (isStreaming ? stopStreaming() : startStreaming())}
            >
              <Ionicons
                name={isStreaming ? 'radio' : 'radio-outline'}
                size={16}
                color={isStreaming ? '#fff' : PRIMARY}
              />
              <Text
                style={[
                  styles.streamButtonText,
                  { color: isStreaming ? '#fff' : PRIMARY },
                ]}
              >
                {isStreaming ? 'Stop Live Mic Stream' : '⚡ Start Live Mic Stream'}
              </Text>
            </TouchableOpacity>
          </View>
          {!isLiveAudioSupported() && (
            <Text style={[styles.streamHint, isDark && styles.textDark]}>
              Live mic requires a development build (not Expo Go).
            </Text>
          )}
          {isStreaming && (
            <View style={styles.processingRow}>
              <ActivityIndicator color={PRIMARY} size="small" />
              <Text style={[styles.processingText, isDark && styles.textDark]}>
                Streaming microphone audio & tokens over /ws/stream…
              </Text>
            </View>
          )}
          <VoiceRecorder
            onRecordingComplete={handleVoiceRecorded}
            disabled={isTranscribing || isStreaming}
          />
          {isTranscribing && (
            <View style={styles.processingRow}>
              <ActivityIndicator color={PRIMARY} size="small" />
              <Text style={[styles.processingText, isDark && styles.textDark]}>
                Transcribing audio…
              </Text>
            </View>
          )}
        </>
      )}

      {inputMode === 'image' && (
        <>
          <ImagePickerButton
            onImageSelected={handleImageSelected}
            disabled={isOcrProcessing}
          />
          {isOcrProcessing && (
            <View style={styles.processingRow}>
              <ActivityIndicator color={PRIMARY} size="small" />
              <Text style={[styles.processingText, isDark && styles.textDark]}>
                Extracting text from image…
              </Text>
            </View>
          )}
        </>
      )}

      {/* ── Vietnamese Text Preview ── */}
      {(vietnameseText.length > 0 || isProcessingInput) && (
        <View style={[styles.vietnameseCard, isDark && styles.vietnameseCardDark]}>
          <View style={styles.cardHeader}>
            <View style={styles.badge}>
              <Text style={styles.badgeText}>VI</Text>
            </View>
            <Text style={[styles.cardLabel, isDark && styles.textDark]}>
              Vietnamese text
            </Text>
          </View>
          {isProcessingInput ? (
            <ActivityIndicator color={PRIMARY} style={{ marginTop: 8 }} />
          ) : (
            <Text style={[styles.vietnameseText, isDark && styles.vietnameseTextDark]}>
              {vietnameseText}
            </Text>
          )}
        </View>
      )}

      {/* ── Context Input ── */}
      <ContextInput value={context} onChangeText={setContext} />

      {/* ── Language Picker ── */}
      <LanguagePicker selectedCode={targetLanguage} onSelect={setTargetLanguage} />

      {/* ── Translate Button ── */}
      <TouchableOpacity
        style={[
          styles.translateButton,
          (!vietnameseText.trim() || isTranslating) && styles.translateButtonDisabled,
        ]}
        onPress={translate}
        disabled={!vietnameseText.trim() || isTranslating}
        activeOpacity={0.85}
        accessibilityLabel="Translate"
      >
        {isTranslating ? (
          <ActivityIndicator color="#fff" size="small" />
        ) : (
          <Ionicons name="swap-horizontal" size={20} color="#fff" />
        )}
        <Text style={styles.translateLabel}>
          {isTranslating ? 'Translating…' : 'Translate'}
        </Text>
      </TouchableOpacity>

      {/* ── Translation Result ── */}
      {translatedText ? (
        <TranslationResult
          translatedText={translatedText}
          sourceLanguage={sourceLanguage}
          targetLanguage={targetLanguage}
        />
      ) : null}

      {/* ── Voice Cloning Panel ── */}
      <VoiceCloningPanel
        translatedText={translatedText}
        targetLanguage={targetLanguage}
        isSynthesizing={isSynthesizing}
        synthesizedAudioUri={synthesizedAudioUri}
        onRecordReference={setReferenceAudio}
        onSynthesize={synthesize}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#f5f5fa',
  },
  screenDark: {
    backgroundColor: '#0d0d1a',
  },
  content: {
    padding: 16,
    paddingBottom: 40,
  },
  errorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#EF4444',
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
    gap: 8,
  },
  errorText: {
    flex: 1,
    color: '#fff',
    fontSize: 13,
  },
  textInput: {
    backgroundColor: '#fff',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 14,
    fontSize: 15,
    color: '#222',
    minHeight: 110,
    marginBottom: 12,
  },
  textInputDark: {
    backgroundColor: '#1a1a2e',
    borderColor: '#2a2a3e',
    color: '#eee',
  },
  processingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
    paddingHorizontal: 4,
  },
  processingText: {
    color: '#555',
    fontSize: 14,
  },
  textDark: {
    color: '#ddd',
  },
  vietnameseCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e0e0f0',
  },
  vietnameseCardDark: {
    backgroundColor: '#1a1a2e',
    borderColor: '#2a2a3e',
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  badge: {
    backgroundColor: '#e0e0f0',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#555',
  },
  cardLabel: {
    fontSize: 13,
    color: '#666',
    fontWeight: '500',
  },
  vietnameseText: {
    fontSize: 15,
    color: '#222',
    lineHeight: 22,
  },
  vietnameseTextDark: {
    color: '#eee',
  },
  translateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: PRIMARY,
    borderRadius: 14,
    paddingVertical: 16,
    marginBottom: 16,
    gap: 10,
    shadowColor: PRIMARY,
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.35,
    shadowRadius: 6,
    elevation: 4,
  },
  translateButtonDisabled: {
    opacity: 0.5,
  },
  translateLabel: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  streamControlRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: 12,
  },
  streamButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 18,
    borderRadius: 20,
    gap: 8,
    borderWidth: 1.5,
  },
  streamButtonInactive: {
    borderColor: PRIMARY,
    backgroundColor: 'transparent',
  },
  streamButtonActive: {
    borderColor: '#EF4444',
    backgroundColor: '#EF4444',
  },
  streamButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },
  streamHint: {
    color: '#777',
    fontSize: 12,
    textAlign: 'center',
    marginBottom: 12,
  },
});
