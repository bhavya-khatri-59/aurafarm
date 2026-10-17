import { Image } from 'expo-image';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import Markdown from 'react-native-markdown-display';

import { DiagnosisCard } from './DiagnosisCard';
import { authHeaders } from '@/lib/api';
import { API_URL } from '@/lib/config';
import type { Diagnosis } from '@/lib/types';
import { colors, radius } from '@/theme';

export type ChatItem = {
  key: string;
  role: 'user' | 'assistant';
  content: string;
  imageId?: string | null;
  localImageUri?: string;
  diagnosis?: Diagnosis | null;
  pending?: boolean;
  status?: string | null;
  error?: string | null;
};

export function MessageBubble({ item }: { item: ChatItem }) {
  if (item.role === 'user') {
    const imageUri = item.localImageUri ?? (item.imageId ? `${API_URL}/uploads/${item.imageId}` : null);
    return (
      <View style={[styles.row, styles.rowUser]}>
        <View style={[styles.bubble, styles.userBubble]}>
          {imageUri && (
            <Image
              source={{ uri: imageUri, headers: item.localImageUri ? undefined : authHeaders() }}
              style={styles.image}
              contentFit="cover"
              transition={150}
            />
          )}
          {!!item.content && <Text style={styles.userText}>{item.content}</Text>}
        </View>
      </View>
    );
  }

  return (
    <View style={styles.row}>
      <View style={[styles.bubble, styles.assistantBubble]}>
        {item.diagnosis && <DiagnosisCard diagnosis={item.diagnosis} />}
        {item.content ? (
          <Markdown style={markdownStyles}>{item.content}</Markdown>
        ) : item.pending ? (
          <View style={styles.statusRow}>
            <ActivityIndicator size="small" color={colors.primary} />
            <Text style={styles.statusText}>{item.status ?? 'Thinking…'}</Text>
          </View>
        ) : null}
        {item.pending && !!item.content && item.status && <Text style={styles.statusText}>{item.status}</Text>}
        {!!item.error && <Text style={styles.failed}>{item.error}</Text>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', paddingHorizontal: 12, marginVertical: 4 },
  rowUser: { justifyContent: 'flex-end' },
  bubble: { maxWidth: '88%', borderRadius: radius.lg, paddingHorizontal: 14, paddingVertical: 10 },
  userBubble: { backgroundColor: colors.userBubble, borderBottomRightRadius: 6 },
  assistantBubble: {
    backgroundColor: colors.assistantBubble,
    borderBottomLeftRadius: 6,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    flexShrink: 1,
  },
  userText: { color: '#fff', fontSize: 16, lineHeight: 22 },
  image: { width: 220, height: 220, borderRadius: radius.md, marginBottom: 6 },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 2 },
  statusText: { color: colors.textMuted, fontSize: 14, fontStyle: 'italic' },
  failed: { color: colors.danger, fontSize: 14 },
});

const markdownStyles = StyleSheet.create({
  body: { color: colors.text, fontSize: 16, lineHeight: 23 },
  heading1: { fontSize: 20, fontWeight: '700', marginVertical: 6 },
  heading2: { fontSize: 18, fontWeight: '700', marginVertical: 6 },
  heading3: { fontSize: 16, fontWeight: '700', marginVertical: 4 },
  link: { color: colors.primary },
  bullet_list: { marginVertical: 4 },
  code_inline: { backgroundColor: colors.primarySoft },
});
