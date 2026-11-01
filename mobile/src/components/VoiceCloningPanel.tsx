import React, { useRef, useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  useColorScheme,
} from 'react-native';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import VoiceRecorder from './VoiceRecorder';

interface Props {
  translatedText: string;
  targetLanguage: string;
  isSynthesizing: boolean;
  synthesizedAudioUri: string | null;
  referenceText: string;
  onRecordReference: (uri: string) => void;
  onReferenceTextChange: (text: string) => void;
  onSynthesize: () => void;
}

const PRIMARY = '#4F46E5';
const MIN_DURATION_MS = 3000;

export default function VoiceCloningPanel({
  translatedText,
  targetLanguage,
  isSynthesizing,
  synthesizedAudioUri,
  referenceText,
  onRecordReference,
  onReferenceTextChange,
  onSynthesize,
}: Props) {
  const scheme = useColorScheme();
  const isDark = scheme === 'dark';
  const isTtsUnavailable = targetLanguage === 'vi';

  const [referenceRecorded, setReferenceRecorded] = useState(false);
  const [isPlayingOutput, setIsPlayingOutput] = useState(false);
  const [isLoadingOutput, setIsLoadingOutput] = useState(false);
  const outputSoundRef = useRef<Audio.Sound | null>(null);

  useEffect(() => {
    return () => {
      outputSoundRef.current?.unloadAsync().catch(() => null);
    };
  }, []);

  // Reset playback when new audio is ready
  useEffect(() => {
    outputSoundRef.current?.unloadAsync().catch(() => null);
    outputSoundRef.current = null;
    setIsPlayingOutput(false);
  }, [synthesizedAudioUri]);

  const handleReferenceRecorded = useCallback(
    (uri: string) => {
      setReferenceRecorded(true);
      onRecordReference(uri);
    },
    [onRecordReference],
  );

  const playOutput = useCallback(async () => {
    if (!synthesizedAudioUri) return;
    if (isPlayingOutput) {
      await outputSoundRef.current?.stopAsync();
      setIsPlayingOutput(false);
      return;
    }
    setIsLoadingOutput(true);
    try {
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
      if (outputSoundRef.current) {
        await outputSoundRef.current.unloadAsync();
      }
      const { sound } = await Audio.Sound.createAsync({
        uri: synthesizedAudioUri,
      });
      outputSoundRef.current = sound;
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          setIsPlayingOutput(false);
        }
      });
      await sound.playAsync();
      setIsPlayingOutput(true);
    } catch (err) {
      console.error('Output playback error', err);
    } finally {
      setIsLoadingOutput(false);
    }
  }, [synthesizedAudioUri, isPlayingOutput]);

  return (
    <View style={[styles.panel, isDark && styles.panelDark]}>
      <View style={styles.panelHeader}>
        <Ionicons name="mic-circle" size={22} color={PRIMARY} />
        <Text style={[styles.panelTitle, isDark && styles.textDark]}>
          Voice Cloning & TTS
        </Text>
      </View>

      {isTtsUnavailable ? (
        <View style={styles.unavailableBox}>
          <Ionicons name="information-circle" size={18} color="#F59E0B" />
          <Text style={styles.unavailableText}>
            TTS is not available when the target language is Vietnamese.
          </Text>
        </View>
      ) : (
        <>
          {/* Reference Voice Recorder */}
          <Text style={[styles.sectionLabel, isDark && styles.textDark]}>
            1. Record reference voice{' '}
            <Text style={styles.hint}>(≥ 3 seconds)</Text>
          </Text>
          <VoiceRecorder
            onRecordingComplete={handleReferenceRecorded}
            disabled={isSynthesizing}
          />

          {/* Reference Text (Optional) */}
          <Text style={[styles.sectionLabel, isDark && styles.textDark]}>
            2. Reference text{' '}
            <Text style={styles.hint}>(optional, improves cloning)</Text>
          </Text>
          <TextInput
            style={[styles.textInput, isDark && styles.textInputDark]}
            value={referenceText}
            onChangeText={onReferenceTextChange}
            placeholder="Type what you said in the reference recording..."
            placeholderTextColor={isDark ? '#555' : '#bbb'}
            multiline
            numberOfLines={2}
            textAlignVertical="top"
            editable={!isSynthesizing}
          />

          {/* Synthesize Button */}
          <TouchableOpacity
            style={[
              styles.synthesizeButton,
              (!translatedText || isSynthesizing) && styles.synthesizeButtonDisabled,
            ]}
            onPress={onSynthesize}
            disabled={!translatedText || isSynthesizing}
            activeOpacity={0.8}
            accessibilityLabel="Generate speech"
          >
            {isSynthesizing ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <Ionicons name="volume-high" size={20} color="#fff" />
            )}
            <Text style={styles.synthesizeLabel}>
              {isSynthesizing ? 'Generating…' : 'Generate Speech'}
            </Text>
          </TouchableOpacity>

          {/* Synthesized Audio Playback */}
          {synthesizedAudioUri && (
            <View style={[styles.outputPlayer, isDark && styles.outputPlayerDark]}>
              <Ionicons name="musical-notes" size={20} color={PRIMARY} />
              <Text style={[styles.outputLabel, isDark && styles.textDark]}>
                Synthesized audio ready
              </Text>
              <TouchableOpacity
                style={styles.playOutputButton}
                onPress={playOutput}
                disabled={isLoadingOutput}
                accessibilityLabel={isPlayingOutput ? 'Stop synthesized audio' : 'Play synthesized audio'}
              >
                {isLoadingOutput ? (
                  <ActivityIndicator color={PRIMARY} size="small" />
                ) : (
                  <Ionicons
                    name={isPlayingOutput ? 'pause-circle' : 'play-circle'}
                    size={36}
                    color={PRIMARY}
                  />
                )}
              </TouchableOpacity>
            </View>
          )}
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  panel: {
    backgroundColor: '#f8f8ff',
    borderRadius: 16,
    padding: 16,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#e0e0f0',
  },
  panelDark: {
    backgroundColor: '#1a1a2e',
    borderColor: '#2a2a3e',
  },
  panelHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
  },
  panelTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#222',
  },
  textDark: {
    color: '#ddd',
  },
  unavailableBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    backgroundColor: '#FFFBEB',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#FDE68A',
  },
  unavailableText: {
    flex: 1,
    fontSize: 14,
    color: '#92400E',
    lineHeight: 20,
  },
  sectionLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  hint: {
    fontWeight: '400',
    color: '#999',
  },
  textInput: {
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 10,
    fontSize: 14,
    color: '#222',
    minHeight: 60,
    marginBottom: 14,
  },
  textInputDark: {
    backgroundColor: '#12122a',
    borderColor: '#333',
    color: '#eee',
  },
  synthesizeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: PRIMARY,
    borderRadius: 10,
    paddingVertical: 14,
    gap: 8,
    shadowColor: PRIMARY,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 3,
  },
  synthesizeButtonDisabled: {
    opacity: 0.5,
  },
  synthesizeLabel: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
  outputPlayer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 16,
    backgroundColor: '#eef',
    borderRadius: 12,
    padding: 12,
    gap: 8,
  },
  outputPlayerDark: {
    backgroundColor: '#12122a',
  },
  outputLabel: {
    flex: 1,
    fontSize: 14,
    color: '#333',
    fontWeight: '500',
  },
  playOutputButton: {
    padding: 4,
  },
});
