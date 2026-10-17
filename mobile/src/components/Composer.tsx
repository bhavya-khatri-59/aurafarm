import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { Alert, Pressable, StyleSheet, TextInput, View } from 'react-native';

import { colors, radius } from '@/theme';

export type PickedImage = { uri: string; mimeType: string };

type Props = {
  text: string;
  onChangeText: (text: string) => void;
  image: PickedImage | null;
  onChangeImage: (image: PickedImage | null) => void;
  onSend: () => void;
  disabled: boolean;
};

const PICKER_OPTIONS: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.8 };

export function Composer({ text, onChangeText, image, onChangeImage, onSend, disabled }: Props) {
  const pick = async (source: 'camera' | 'library') => {
    const permission =
      source === 'camera'
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Permission needed', `Allow ${source === 'camera' ? 'camera' : 'photo'} access to add a picture.`);
      return;
    }
    const result =
      source === 'camera'
        ? await ImagePicker.launchCameraAsync(PICKER_OPTIONS)
        : await ImagePicker.launchImageLibraryAsync(PICKER_OPTIONS);
    if (!result.canceled && result.assets[0]) {
      const asset = result.assets[0];
      onChangeImage({ uri: asset.uri, mimeType: asset.mimeType ?? 'image/jpeg' });
    }
  };

  const canSend = !disabled && (text.trim().length > 0 || image !== null);

  return (
    <View style={styles.container}>
      {image && (
        <View style={styles.preview}>
          <Image source={{ uri: image.uri }} style={styles.previewImage} contentFit="cover" />
          <Pressable style={styles.removeImage} onPress={() => onChangeImage(null)} hitSlop={8} accessibilityLabel="Remove photo">
            <Ionicons name="close" size={14} color="#fff" />
          </Pressable>
        </View>
      )}
      <View style={styles.row}>
        <Pressable onPress={() => pick('camera')} style={styles.iconButton} accessibilityLabel="Take a photo">
          <Ionicons name="camera-outline" size={24} color={colors.primary} />
        </Pressable>
        <Pressable onPress={() => pick('library')} style={styles.iconButton} accessibilityLabel="Choose a photo">
          <Ionicons name="image-outline" size={24} color={colors.primary} />
        </Pressable>
        <TextInput
          style={styles.input}
          value={text}
          onChangeText={onChangeText}
          placeholder={image ? 'Add a note about this plant (optional)' : 'Ask about your crops…'}
          placeholderTextColor={colors.textMuted}
          multiline
          maxLength={4000}
        />
        <Pressable
          onPress={onSend}
          disabled={!canSend}
          style={[styles.send, !canSend && { backgroundColor: colors.border }]}
          accessibilityLabel="Send"
        >
          <Ionicons name="arrow-up" size={20} color="#fff" />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    backgroundColor: colors.surface,
    paddingHorizontal: 8,
    paddingTop: 8,
    paddingBottom: 8,
  },
  preview: { marginLeft: 8, marginBottom: 8, width: 72, height: 72 },
  previewImage: { width: 72, height: 72, borderRadius: radius.sm },
  removeImage: {
    position: 'absolute',
    top: -6,
    right: -6,
    backgroundColor: colors.text,
    borderRadius: 10,
    width: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  row: { flexDirection: 'row', alignItems: 'flex-end', gap: 4 },
  iconButton: { padding: 8 },
  input: {
    flex: 1,
    maxHeight: 120,
    backgroundColor: colors.background,
    borderRadius: radius.lg,
    paddingHorizontal: 14,
    paddingTop: 10,
    paddingBottom: 10,
    fontSize: 16,
    color: colors.text,
  },
  send: {
    backgroundColor: colors.primary,
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 4,
  },
});
