/**
 * useVoiceRecording — ghi âm bằng expo-av (chế độ "ghi rồi nhận dạng", dùng khi
 * thiết bị không hỗ trợ nghe trực tiếp, ví dụ Expo Go).
 *
 * Trả về:
 *   start()  — xin quyền micro + bắt đầu ghi
 *   stop()   — dừng ghi, trả về uri file (hoặc null)
 *   cancel() — dừng ghi và bỏ kết quả (không trả uri)
 */

import { useRef, useCallback, useEffect } from 'react';
import { Audio } from 'expo-av';

export interface UseVoiceRecordingResult {
  start: () => Promise<void>;
  stop: () => Promise<string | null>;
  cancel: () => Promise<void>;
}

export function useVoiceRecording(): UseVoiceRecordingResult {
  const recordingRef = useRef<Audio.Recording | null>(null);

  const start = useCallback(async () => {
    const permission = await Audio.requestPermissionsAsync();
    if (permission.status !== 'granted') {
      throw new Error('MICROPHONE_PERMISSION_DENIED');
    }

    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
    });

    const { recording } = await Audio.Recording.createAsync(
      Audio.RecordingOptionsPresets.HIGH_QUALITY,
    );
    recordingRef.current = recording;
  }, []);

  const stop = useCallback(async (): Promise<string | null> => {
    const recording = recordingRef.current;
    recordingRef.current = null;
    if (!recording) return null;

    try {
      await recording.stopAndUnloadAsync();
    } catch {
      // Recorder có thể đã dừng sẵn.
    }

    const uri = recording.getURI() ?? null;
    void Audio.setAudioModeAsync({ allowsRecordingIOS: false }).catch(
      () => undefined,
    );
    return uri;
  }, []);

  const cancel = useCallback(async () => {
    const recording = recordingRef.current;
    recordingRef.current = null;
    if (!recording) return;
    try {
      await recording.stopAndUnloadAsync();
    } catch {
      // Bỏ qua.
    }
    void Audio.setAudioModeAsync({ allowsRecordingIOS: false }).catch(
      () => undefined,
    );
  }, []);

  // Giải phóng recorder khi unmount.
  useEffect(() => {
    return () => {
      void cancel();
    };
  }, [cancel]);

  return { start, stop, cancel };
}
