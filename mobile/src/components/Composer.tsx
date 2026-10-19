import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import * as ImagePicker from 'expo-image-picker';
import { Alert, Pressable, StyleSheet, TextInput, View } from 'react-native';

import { useTheme, useThemedStyles } from '@/lib/theme';
import { radius, type Colors } from '@/theme';

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
  const { colors } = useTheme();
  const styles = useThemedStyles(makeStyles);

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
          <Pressable
            style={styles.removeImage}
            onPress={() => onChangeImage(null)}
            hitSlop={8}
            accessibilityLabel="Remove photo"
          >
            <Ionicons name="close" size={14} color={colors.surface} />
          </Pressable>
        </View>
      )}
      <View style={styles.bar}>
        <Pressable
          onPress={() => pick('camera')}
          style={styles.iconButton}
          hitSlop={4}
          accessibilityLabel="Take a photo"
        >
          <Ionicons name="camera-outline" size={23} color={colors.primary} />
        </Pressable>
        <Pressable
          onPress={() => pick('library')}
          style={styles.iconButton}
          hitSlop={4}
          accessibilityLabel="Choose a photo"
        >
          <Ionicons name="image-outline" size={22} color={colors.primary} />
        </Pressable>
        <TextInput
          style={styles.input}
          value={text}
          onChangeText={onChangeText}
          placeholder={image ? 'Add a note (optional)' : 'Ask about your crops…'}
          placeholderTextColor={colors.textMuted}
          multiline
          maxLength={4000}
        />
        <Pressable
          onPress={onSend}
          disabled={!canSend}
          style={[styles.send, !canSend && styles.sendDisabled]}
          accessibilityLabel="Send"
        >
          <Ionicons name="arrow-up" size={20} color={canSend ? colors.onPrimary : colors.textMuted} />
        </Pressable>
      </View>
    </View>
  );
}

const makeStyles = (colors: Colors) =>
  StyleSheet.create({
    container: { paddingHorizontal: 10, paddingTop: 6, paddingBottom: 8 },
    preview: { marginLeft: 6, marginBottom: 8, width: 72, height: 72 },
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
    bar: {
      flexDirection: 'row',
      alignItems: 'flex-end',
      backgroundColor: colors.surface,
      borderRadius: radius.lg + 4,
      borderWidth: StyleSheet.hairlineWidth,
      borderColor: colors.border,
      paddingHorizontal: 6,
      paddingVertical: 5,
      shadowColor: colors.shadow,
      shadowOpacity: 0.07,
      shadowRadius: 8,
      shadowOffset: { width: 0, height: 2 },
      elevation: 2,
    },
    iconButton: { paddingHorizontal: 6, paddingVertical: 8 },
    input: {
      flex: 1,
      maxHeight: 120,
      paddingHorizontal: 8,
      paddingTop: 9,
      paddingBottom: 9,
      fontSize: 16,
      color: colors.text,
    },
    send: {
      backgroundColor: colors.primary,
      width: 38,
      height: 38,
      borderRadius: 19,
      alignItems: 'center',
      justifyContent: 'center',
      marginLeft: 4,
    },
    sendDisabled: { backgroundColor: colors.surfaceMuted },
  });
