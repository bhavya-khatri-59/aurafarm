import { useEffect, useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { colors, radius } from '@/theme';

type Props = {
  visible: boolean;
  initialTitle: string;
  onCancel: () => void;
  onSave: (title: string) => void;
};

export function RenameModal({ visible, initialTitle, onCancel, onSave }: Props) {
  const [title, setTitle] = useState(initialTitle);
  useEffect(() => setTitle(initialTitle), [initialTitle, visible]);
  const save = () => title.trim() && onSave(title.trim());

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <View style={styles.backdrop}>
        <View style={styles.card}>
          <Text style={styles.title}>Rename conversation</Text>
          <TextInput
            style={styles.input}
            value={title}
            onChangeText={setTitle}
            autoFocus
            maxLength={200}
            onSubmitEditing={save}
          />
          <View style={styles.actions}>
            <Pressable onPress={onCancel} style={styles.action}>
              <Text style={styles.cancel}>Cancel</Text>
            </Pressable>
            <Pressable onPress={save} style={styles.action}>
              <Text style={styles.save}>Save</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.35)', justifyContent: 'center', padding: 24 },
  card: { backgroundColor: colors.surface, borderRadius: radius.md, padding: 20 },
  title: { fontSize: 17, fontWeight: '600', color: colors.text, marginBottom: 12 },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    color: colors.text,
  },
  actions: { flexDirection: 'row', justifyContent: 'flex-end', marginTop: 16, gap: 8 },
  action: { paddingHorizontal: 14, paddingVertical: 8 },
  cancel: { color: colors.textMuted, fontSize: 16 },
  save: { color: colors.primary, fontSize: 16, fontWeight: '600' },
});
