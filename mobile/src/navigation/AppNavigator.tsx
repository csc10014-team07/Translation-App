import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { RootStackParamList } from './types';
import { useTheme } from '../theme/ThemeProvider';
import HomeScreen from '../screens/HomeScreen';
import TargetLanguageScreen from '../screens/TargetLanguageScreen';
import SourceLanguageScreen from '../screens/SourceLanguageScreen';
import VoiceListeningScreen from '../screens/VoiceListeningScreen';
import CameraScreen from '../screens/CameraScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function AppNavigator() {
  const { colors } = useTheme();

  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.background },
        animation: 'slide_from_right',
      }}
    >
      <Stack.Screen name="Home" component={HomeScreen} />

      <Stack.Screen name="TargetLanguage" component={TargetLanguageScreen} />
      <Stack.Screen
        name="SourceLanguage"
        component={SourceLanguageScreen}
        options={{ animation: 'slide_from_right' }}
      />

      <Stack.Screen
        name="VoiceListening"
        component={VoiceListeningScreen}
        options={{
          presentation: 'fullScreenModal',
          animation: 'slide_from_bottom',
          gestureEnabled: false,
        }}
      />
      <Stack.Screen
        name="Camera"
        component={CameraScreen}
        options={{
          presentation: 'fullScreenModal',
          animation: 'slide_from_bottom',
          gestureEnabled: false,
        }}
      />
    </Stack.Navigator>
  );
}
