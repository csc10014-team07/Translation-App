import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  StyleSheet,
  View,
} from 'react-native';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from '../theme/ThemeProvider';
import ThemedText from '../theme/ThemedText';
import IconCircleButton from './IconCircleButton';
import OutlineButton from './OutlineButton';
import PrimaryButton from './PrimaryButton';
import { useVoiceRecording } from '../hooks/useVoiceRecording';
import {
  VOICE_CLONE_MAX_DURATION_S,
  VOICE_CLONE_MIN_DURATION_S,
} from '../constants/voice';
import { strings } from '../constants/strings';
import { formatMmSs } from '../utils/formatTime';
import { s, vs, ms } from '../utils/scale';

interface Props {
  visible: boolean;
  initialUri: string | null;
  onClose: () => void;
  onUse: (uri: string) => void;
  onClear: () => void;
}

type Phase = 'idle' | 'recording' | 'recorded';

const TIMER_INTERVAL_MS = 100;

export default function VoiceCloneSheet({
  visible,
  initialUri,
  onClose,
  onUse,
  onClear,
}: Props) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const { start, stop, cancel } = useVoiceRecording();

  const [phase, setPhase] = useState<Phase>(initialUri ? 'recorded' : 'idle');
  const [recordedUri, setRecordedUri] = useState<string | null>(initialUri);
  const [elapsedS, setElapsedS] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [busy, setBusy] = useState(false);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startedAtRef = useRef(0);
  const soundRef = useRef<Audio.Sound | null>(null);
  const stoppingRef = useRef(false);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const unloadSound = useCallback(async () => {
    const sound = soundRef.current;
    soundRef.current = null;
    setPlaying(false);
    if (sound) {
      try {
        await sound.stopAsync();
        await sound.unloadAsync();
      } catch {
        // Ignore unload failures.
      }
    }
  }, []);

  const resetToInitial = useCallback(() => {
    stopTimer();
    stoppingRef.current = false;
    setPhase(initialUri ? 'recorded' : 'idle');
    setRecordedUri(initialUri);
    setElapsedS(0);
    setError(null);
    setBusy(false);
    void unloadSound();
  }, [initialUri, stopTimer, unloadSound]);

  useEffect(() => {
    if (visible) {
      resetToInitial();
    } else {
      stopTimer();
      void cancel();
      void unloadSound();
    }
  }, [visible, resetToInitial, stopTimer, cancel, unloadSound]);

  useEffect(() => {
    return () => {
      stopTimer();
      void cancel();
      void unloadSound();
    };
  }, [stopTimer, cancel, unloadSound]);

  const finishRecording = useCallback(async () => {
    if (stoppingRef.current) return;
    stoppingRef.current = true;
    stopTimer();

    const duration = (Date.now() - startedAtRef.current) / 1000;
    const uri = await stop();

    if (!uri) {
      stoppingRef.current = false;
      setPhase('idle');
      setError(strings.voiceClone.recordError);
      return;
    }
    if (duration < VOICE_CLONE_MIN_DURATION_S) {
      stoppingRef.current = false;
      setPhase(initialUri ? 'recorded' : 'idle');
      setRecordedUri(initialUri);
      setError(strings.voiceClone.tooShort);
      return;
    }

    setRecordedUri(uri);
    setPhase('recorded');
    setElapsedS(Math.min(duration, VOICE_CLONE_MAX_DURATION_S));
    setError(null);
    stoppingRef.current = false;
  }, [stop, stopTimer]);

  const handleRecord = useCallback(async () => {
    setError(null);
    setBusy(true);
    await unloadSound();
    try {
      await start();
      setRecordedUri(null);
      setPhase('recording');
      setElapsedS(0);
      startedAtRef.current = Date.now();
      stoppingRef.current = false;

      timerRef.current = setInterval(() => {
        const elapsed = (Date.now() - startedAtRef.current) / 1000;
        setElapsedS(Math.min(elapsed, VOICE_CLONE_MAX_DURATION_S));
        if (elapsed >= VOICE_CLONE_MAX_DURATION_S) {
          void finishRecording();
        }
      }, TIMER_INTERVAL_MS);
    } catch (e) {
      setPhase(initialUri ? 'recorded' : 'idle');
      setRecordedUri(initialUri);
      setError(
        e instanceof Error && e.message === 'MICROPHONE_PERMISSION_DENIED'
          ? strings.voiceClone.permissionDenied
          : strings.voiceClone.recordError,
      );
    } finally {
      setBusy(false);
    }
  }, [start, finishRecording, initialUri, unloadSound]);

  const handlePlay = useCallback(async () => {
    if (!recordedUri) return;
    if (playing) {
      await unloadSound();
      return;
    }
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
      });
      await unloadSound();
      const { sound } = await Audio.Sound.createAsync({ uri: recordedUri });
      soundRef.current = sound;
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          setPlaying(false);
        }
      });
      await sound.playAsync();
      setPlaying(true);
    } catch {
      setError(strings.voiceClone.recordError);
    }
  }, [playing, recordedUri, unloadSound]);

  const handleClose = useCallback(() => {
    stopTimer();
    void cancel();
    void unloadSound();
    onClose();
  }, [stopTimer, cancel, unloadSound, onClose]);

  const handleUse = useCallback(() => {
    if (!recordedUri) return;
    onUse(recordedUri);
    handleClose();
  }, [recordedUri, onUse, handleClose]);

  const handleClear = useCallback(() => {
    stopTimer();
    stoppingRef.current = false;
    setPhase('idle');
    setRecordedUri(null);
    setElapsedS(0);
    setError(null);
    setBusy(false);
    void unloadSound();
    onClear();
  }, [stopTimer, unloadSound, onClear]);

  const isRecording = phase === 'recording';
  const canUse = phase === 'recorded' && recordedUri !== null;

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={handleClose}
    >
      <View style={styles.backdrop}>
        <Pressable style={styles.backdropTouchable} onPress={handleClose} />
        <View
          style={[
            styles.sheet,
            {
              backgroundColor: colors.surface,
              paddingBottom: vs(20) + insets.bottom,
            },
          ]}
        >
          <View style={styles.handle} />

          <View style={styles.header}>
            <ThemedText variant="screenTitle" style={styles.title}>
              {strings.voiceClone.title}
            </ThemedText>
            <IconCircleButton
              icon="close"
              size="small"
              variant="neutral"
              accessibilityLabel={strings.voiceClone.close}
              onPress={handleClose}
            />
          </View>

          <ThemedText
            style={[styles.description, { color: colors.textSecondary }]}
          >
            {strings.voiceClone.description}
          </ThemedText>

          <View
            style={[
              styles.stage,
              {
                backgroundColor: colors.surfaceMuted,
                borderColor: colors.border,
              },
            ]}
          >
            <Ionicons
              name={isRecording ? 'mic' : 'mic-outline'}
              size={ms(34)}
              color={isRecording ? colors.danger : colors.primary}
            />
            <ThemedText style={[styles.timer, { color: colors.textPrimary }]}>
              {`${formatMmSs(elapsedS)} / ${formatMmSs(
                VOICE_CLONE_MAX_DURATION_S,
              )}`}
            </ThemedText>
            <ThemedText
              style={[styles.stageHint, { color: colors.textSecondary }]}
            >
              {isRecording
                ? strings.voiceClone.recordingHint
                : phase === 'recorded'
                  ? strings.voiceClone.ready
                  : strings.voiceClone.description}
            </ThemedText>
          </View>

          {error !== null && (
            <ThemedText style={[styles.error, { color: colors.danger }]}>
              {error}
            </ThemedText>
          )}

          <View style={styles.actions}>
            {phase === 'idle' && (
              <PrimaryButton
                label={strings.voiceClone.record}
                iconLeft="mic-outline"
                onPress={handleRecord}
                loading={busy}
                accessibilityLabel={strings.voiceClone.accessibilityRecord}
              />
            )}

            {isRecording && (
              <PrimaryButton
                label={strings.voiceClone.stop}
                iconLeft="stop"
                onPress={() => void finishRecording()}
                accessibilityLabel={strings.voiceClone.accessibilityStop}
              />
            )}

            {phase === 'recorded' && (
              <>
                <PrimaryButton
                  label={strings.voiceClone.use}
                  iconLeft="checkmark"
                  onPress={handleUse}
                  accessibilityLabel={strings.voiceClone.accessibilityUse}
                />
                <View style={{ height: vs(10) }} />
                <View style={styles.secondaryRow}>
                  <OutlineButton
                    label={
                      playing
                        ? strings.voiceClone.stopPlay
                        : strings.voiceClone.play
                    }
                    iconLeft={playing ? 'stop' : 'play'}
                    fullWidth={false}
                    onPress={handlePlay}
                    accessibilityLabel={strings.voiceClone.accessibilityPlay}
                  />
                  <View style={{ width: s(10) }} />
                  <OutlineButton
                    label={strings.voiceClone.record}
                    iconLeft="mic-outline"
                    tone="danger"
                    fullWidth={false}
                    onPress={handleRecord}
                    disabled={busy}
                    accessibilityLabel={strings.voiceClone.accessibilityRecord}
                  />
                </View>
              </>
            )}
          </View>

          {recordedUri !== null && (
            <View style={{ marginTop: vs(8) }}>
              <OutlineButton
                label={strings.voiceClone.clear}
                iconLeft="trash-outline"
                tone="danger"
                onPress={handleClear}
                accessibilityLabel={strings.voiceClone.accessibilityClear}
              />
            </View>
          )}

          {busy && (
            <ActivityIndicator
              color={colors.primary}
              style={{ marginTop: vs(12) }}
            />
          )}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.45)',
  },
  backdropTouchable: {
    ...StyleSheet.absoluteFillObject,
  },
  sheet: {
    borderTopLeftRadius: s(28),
    borderTopRightRadius: s(28),
    paddingHorizontal: s(21),
    paddingTop: vs(10),
    maxHeight: '90%',
  },
  handle: {
    alignSelf: 'center',
    width: s(42),
    height: vs(5),
    borderRadius: vs(3),
    backgroundColor: 'rgba(128,128,128,0.35)',
    marginBottom: vs(14),
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  title: {
    fontSize: ms(24),
    fontWeight: '700',
  },
  description: {
    fontSize: ms(15),
    lineHeight: ms(21),
    marginTop: vs(8),
  },
  stage: {
    marginTop: vs(16),
    borderRadius: s(22),
    borderWidth: 1,
    paddingVertical: vs(22),
    paddingHorizontal: s(18),
    alignItems: 'center',
  },
  timer: {
    fontSize: ms(30),
    fontWeight: '700',
    marginTop: vs(10),
    fontVariant: ['tabular-nums'],
  },
  stageHint: {
    fontSize: ms(14),
    lineHeight: ms(20),
    textAlign: 'center',
    marginTop: vs(6),
  },
  error: {
    fontSize: ms(14),
    lineHeight: ms(20),
    marginTop: vs(10),
  },
  actions: {
    marginTop: vs(16),
  },
  secondaryRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});
