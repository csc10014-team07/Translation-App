import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  useColorScheme,
} from 'react-native';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';

interface Props {
  onRecordingComplete: (uri: string) => void;
  /** Optional: disable controls while parent is processing */
  disabled?: boolean;
}

const PRIMARY = '#4F46E5';
const DANGER = '#EF4444';

export default function VoiceRecorder({ onRecordingComplete, disabled }: Props) {
  const scheme = useColorScheme();
  const isDark = scheme === 'dark';

  const [permissionStatus, setPermissionStatus] = useState<'undetermined' | 'granted' | 'denied'>('undetermined');
  const [isRecording, setIsRecording] = useState(false);
  const [recordingUri, setRecordingUri] = useState<string | null>(null);
  const [durationMs, setDurationMs] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoadingPlayback, setIsLoadingPlayback] = useState(false);

  const recordingRef = useRef<Audio.Recording | null>(null);
  const soundRef = useRef<Audio.Sound | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Request microphone permission
  useEffect(() => {
    (async () => {
      const { status } = await Audio.requestPermissionsAsync();
      setPermissionStatus(status === 'granted' ? 'granted' : 'denied');
    })();
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopTimer();
      recordingRef.current?.stopAndUnloadAsync().catch(() => null);
      soundRef.current?.unloadAsync().catch(() => null);
    };
  }, []);

  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const startRecording = useCallback(async () => {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY,
      );
      recordingRef.current = recording;
      setIsRecording(true);
      setDurationMs(0);
      setRecordingUri(null);

      timerRef.current = setInterval(() => {
        setDurationMs((prev) => prev + 100);
      }, 100);
    } catch (err) {
      console.error('Failed to start recording', err);
    }
  }, []);

  const stopRecording = useCallback(async () => {
    stopTimer();
    try {
      await recordingRef.current?.stopAndUnloadAsync();
      const uri = recordingRef.current?.getURI();
      recordingRef.current = null;
      setIsRecording(false);
      if (uri) {
        setRecordingUri(uri);
        onRecordingComplete(uri);
      }
    } catch (err) {
      console.error('Failed to stop recording', err);
      setIsRecording(false);
    }
  }, [onRecordingComplete]);

  const playback = useCallback(async () => {
    if (!recordingUri) return;
    if (isPlaying) {
      await soundRef.current?.stopAsync();
      setIsPlaying(false);
      return;
    }
    setIsLoadingPlayback(true);
    try {
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
      if (soundRef.current) {
        await soundRef.current.unloadAsync();
      }
      const { sound } = await Audio.Sound.createAsync({ uri: recordingUri });
      soundRef.current = sound;
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          setIsPlaying(false);
        }
      });
      await sound.playAsync();
      setIsPlaying(true);
    } catch (err) {
      console.error('Playback error', err);
    } finally {
      setIsLoadingPlayback(false);
    }
  }, [recordingUri, isPlaying]);

  const formatDuration = (ms: number) => {
    const totalSeconds = Math.floor(ms / 1000);
    const m = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const s = (totalSeconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  if (permissionStatus === 'denied') {
    return (
      <View style={[styles.container, isDark && styles.containerDark]}>
        <Text style={[styles.permissionText, isDark && styles.textDark]}>
          Microphone permission denied. Please enable it in Settings.
        </Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, isDark && styles.containerDark]}>
      {/* Record Button */}
      <TouchableOpacity
        style={[styles.recordButton, isRecording && styles.recordButtonActive]}
        onPress={isRecording ? stopRecording : startRecording}
        disabled={disabled || permissionStatus !== 'granted'}
        activeOpacity={0.8}
        accessibilityLabel={isRecording ? 'Stop recording' : 'Start recording'}
      >
        {isRecording ? (
          <Ionicons name="stop" size={32} color="#fff" />
        ) : (
          <Ionicons name="mic" size={32} color="#fff" />
        )}
      </TouchableOpacity>

      {/* Duration */}
      <Text style={[styles.duration, isDark && styles.textDark]}>
        {isRecording ? (
          <Text style={styles.durationRecording}>{formatDuration(durationMs)}</Text>
        ) : recordingUri ? (
          formatDuration(durationMs)
        ) : (
          'Tap to record'
        )}
      </Text>

      {/* Playback */}
      {recordingUri && !isRecording && (
        <TouchableOpacity
          style={styles.playbackButton}
          onPress={playback}
          disabled={isLoadingPlayback}
          accessibilityLabel={isPlaying ? 'Stop playback' : 'Play recording'}
        >
          {isLoadingPlayback ? (
            <ActivityIndicator color={PRIMARY} size="small" />
          ) : (
            <Ionicons
              name={isPlaying ? 'pause-circle' : 'play-circle'}
              size={36}
              color={PRIMARY}
            />
          )}
          <Text style={[styles.playbackLabel, isDark && styles.textDark]}>
            {isPlaying ? 'Stop' : 'Play recording'}
          </Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    paddingVertical: 24,
    backgroundColor: '#f8f8ff',
    borderRadius: 16,
    marginBottom: 12,
  },
  containerDark: {
    backgroundColor: '#1a1a2e',
  },
  recordButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: DANGER,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: DANGER,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 6,
    elevation: 5,
  },
  recordButtonActive: {
    backgroundColor: '#991b1b',
  },
  duration: {
    marginTop: 12,
    fontSize: 16,
    color: '#444',
    fontVariant: ['tabular-nums'],
  },
  durationRecording: {
    color: DANGER,
    fontWeight: '700',
  },
  textDark: {
    color: '#ccc',
  },
  playbackButton: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 16,
    gap: 8,
  },
  playbackLabel: {
    fontSize: 15,
    color: PRIMARY,
    fontWeight: '500',
  },
  permissionText: {
    color: '#666',
    textAlign: 'center',
    paddingHorizontal: 16,
  },
});
