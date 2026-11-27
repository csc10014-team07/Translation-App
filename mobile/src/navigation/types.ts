import type { NativeStackScreenProps } from '@react-navigation/native-stack';

export type RootStackParamList = {
  Home: undefined;
  TargetLanguage: undefined;
  SourceLanguage: undefined;
  VoiceListening: { liveSupported?: boolean } | undefined;
  Camera: undefined;
};

/** Kiểu props tiện dụng cho từng màn hình. */
export type HomeScreenProps = NativeStackScreenProps<RootStackParamList, 'Home'>;
export type TargetLanguageScreenProps = NativeStackScreenProps<
  RootStackParamList,
  'TargetLanguage'
>;
export type SourceLanguageScreenProps = NativeStackScreenProps<
  RootStackParamList,
  'SourceLanguage'
>;
export type VoiceListeningScreenProps = NativeStackScreenProps<
  RootStackParamList,
  'VoiceListening'
>;
export type CameraScreenProps = NativeStackScreenProps<RootStackParamList, 'Camera'>;
