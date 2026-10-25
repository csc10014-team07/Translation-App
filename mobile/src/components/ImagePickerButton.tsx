import React, { useState } from 'react';
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  StyleSheet,
  Alert,
  useColorScheme,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Ionicons } from '@expo/vector-icons';

interface Props {
  onImageSelected: (uri: string) => void;
  disabled?: boolean;
}

const PRIMARY = '#4F46E5';

export default function ImagePickerButton({ onImageSelected, disabled }: Props) {
  const scheme = useColorScheme();
  const isDark = scheme === 'dark';
  const [selectedUri, setSelectedUri] = useState<string | null>(null);

  const requestAndPick = async (source: 'camera' | 'gallery') => {
    if (source === 'camera') {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission required', 'Camera permission is needed to take a photo.');
        return;
      }
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.85,
      });
      if (!result.canceled && result.assets[0]) {
        const uri = result.assets[0].uri;
        setSelectedUri(uri);
        onImageSelected(uri);
      }
    } else {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission required', 'Photo library permission is needed to select an image.');
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.85,
      });
      if (!result.canceled && result.assets[0]) {
        const uri = result.assets[0].uri;
        setSelectedUri(uri);
        onImageSelected(uri);
      }
    }
  };

  const showOptions = () => {
    Alert.alert('Select Image Source', 'Choose how to pick an image', [
      { text: 'Camera', onPress: () => requestAndPick('camera') },
      { text: 'Photo Library', onPress: () => requestAndPick('gallery') },
      { text: 'Cancel', style: 'cancel' },
    ]);
  };

  return (
    <View style={[styles.container, isDark && styles.containerDark]}>
      <TouchableOpacity
        style={[styles.button, disabled && styles.buttonDisabled]}
        onPress={showOptions}
        disabled={disabled}
        activeOpacity={0.8}
        accessibilityLabel="Pick an image for OCR"
      >
        <Ionicons name="camera" size={22} color="#fff" />
        <Text style={styles.buttonText}>
          {selectedUri ? 'Change Image' : 'Pick Image'}
        </Text>
      </TouchableOpacity>

      {selectedUri && (
        <View style={styles.previewContainer}>
          <Image
            source={{ uri: selectedUri }}
            style={styles.thumbnail}
            resizeMode="cover"
            accessibilityLabel="Selected image preview"
          />
          <TouchableOpacity
            style={styles.removeButton}
            onPress={() => setSelectedUri(null)}
            accessibilityLabel="Remove selected image"
          >
            <Ionicons name="close-circle" size={22} color="#EF4444" />
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    paddingVertical: 16,
    backgroundColor: '#f8f8ff',
    borderRadius: 16,
    marginBottom: 12,
  },
  containerDark: {
    backgroundColor: '#1a1a2e',
  },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: PRIMARY,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 10,
    gap: 8,
    shadowColor: PRIMARY,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 3,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
  previewContainer: {
    marginTop: 16,
    position: 'relative',
  },
  thumbnail: {
    width: 180,
    height: 130,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: PRIMARY,
  },
  removeButton: {
    position: 'absolute',
    top: -10,
    right: -10,
    backgroundColor: '#fff',
    borderRadius: 12,
  },
});
