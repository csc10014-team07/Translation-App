import type { NativeStackScreenProps } from '@react-navigation/native-stack';

export type RootStackParamList = {
  Home: undefined;
  TargetLanguage: undefined;
  DefaultLanguage: undefined;
  VoiceListening: { liveSupported?: boolean } | undefined;
  Camera: undefined;
};

/** Kiểu props tiện dụng cho từng màn hình. */
export type HomeScreenProps = NativeStackScreenProps<RootStackParamList, 'Home'>;
export type TargetLanguageScreenProps = NativeStackScreenProps<
  RootStackParamList,
  'TargetLanguage'
>;
export type DefaultLanguageScreenProps = NativeStackScreenProps<
  RootStackParamList,
  'DefaultLanguage'
>;
export type VoiceListeningScreenProps = NativeStackScreenProps<
  RootStackParamList,
  'VoiceListening'
>;
export type CameraScreenProps = NativeStackScreenProps<RootStackParamList, 'Camera'>;
