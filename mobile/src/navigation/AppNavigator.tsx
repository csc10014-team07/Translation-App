import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import TranslationScreen from '../screens/TranslationScreen';

export type RootStackParamList = {
  Translation: undefined;
};

const Stack = createStackNavigator<RootStackParamList>();

export default function AppNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: '#4F46E5',
        },
        headerTintColor: '#FFFFFF',
        headerTitleStyle: {
          fontWeight: '700',
        },
      }}
    >
      <Stack.Screen
        name="Translation"
        component={TranslationScreen}
        options={{ title: 'Vietnamese Translation' }}
      />
    </Stack.Navigator>
  );
}
