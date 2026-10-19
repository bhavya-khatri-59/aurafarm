import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import { useMemo } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import Markdown from 'react-native-markdown-display';

import { DiagnosisCard } from './DiagnosisCard';
import { authHeaders } from '@/lib/api';
import { API_URL } from '@/lib/config';
import { useTheme, useThemedStyles } from '@/lib/theme';
import type { Diagnosis } from '@/lib/types';
import { radius, type Colors } from '@/theme';

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
  const { colors } = useTheme();
  const styles = useThemedStyles(makeStyles);
  const markdownStyles = useMemo(() => makeMarkdownStyles(colors), [colors]);

  if (item.role === 'user') {
    const imageUri = item.localImageUri ?? (item.imageId ? `${API_URL}/uploads/${item.imageId}` : null);
    return (
      <View style={[styles.row, styles.rowUser]}>
        <View style={[styles.bubble, styles.userBubble, imageUri ? styles.userBubbleWithImage : null]}>
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
      <View style={styles.avatar}>
        <Ionicons name="leaf" size={14} color={colors.primary} />
      </View>
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
        {!!item.error && (
          <View style={styles.errorRow}>
            <Ionicons name="alert-circle-outline" size={16} color={colors.danger} />
            <Text style={styles.errorText}>{item.error}</Text>
          </View>
        )}
      </View>
    </View>
  );
}

const makeStyles = (colors: Colors) =>
  StyleSheet.create({
    row: { flexDirection: 'row', alignItems: 'flex-end', paddingHorizontal: 12, marginVertical: 5, gap: 8 },
    rowUser: { justifyContent: 'flex-end' },
    avatar: {
      width: 26,
      height: 26,
      borderRadius: 13,
      backgroundColor: colors.primarySoft,
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: 2,
    },
    bubble: {
      maxWidth: '84%',
      borderRadius: radius.lg,
      paddingHorizontal: 14,
      paddingVertical: 10,
      shadowColor: colors.shadow,
      shadowOpacity: 0.06,
      shadowRadius: 6,
      shadowOffset: { width: 0, height: 2 },
      elevation: 1,
    },
    userBubble: { backgroundColor: colors.userBubble, borderBottomRightRadius: 6 },
    userBubbleWithImage: { padding: 5 },
    assistantBubble: { backgroundColor: colors.assistantBubble, borderBottomLeftRadius: 6, flexShrink: 1 },
    userText: { color: colors.userText, fontSize: 16, lineHeight: 22, paddingHorizontal: 0 },
    image: { width: 230, height: 230, borderRadius: radius.md, marginBottom: 4 },
    statusRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 2 },
    statusText: { color: colors.textMuted, fontSize: 14, fontStyle: 'italic' },
    errorRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
    errorText: { flexShrink: 1, color: colors.danger, fontSize: 14 },
  });

const makeMarkdownStyles = (colors: Colors) =>
  StyleSheet.create({
    body: { color: colors.text, fontSize: 16, lineHeight: 23 },
    heading1: { fontSize: 20, fontWeight: '700', marginVertical: 6, color: colors.text },
    heading2: { fontSize: 18, fontWeight: '700', marginVertical: 6, color: colors.text },
    heading3: { fontSize: 16, fontWeight: '700', marginVertical: 4, color: colors.text },
    strong: { fontWeight: '700' },
    link: { color: colors.primary, textDecorationLine: 'underline' },
    bullet_list: { marginVertical: 4 },
    ordered_list: { marginVertical: 4 },
    code_inline: { backgroundColor: colors.surfaceMuted, color: colors.text, borderRadius: 4 },
    fence: { backgroundColor: colors.surfaceMuted, color: colors.text, borderColor: colors.border },
    blockquote: { backgroundColor: colors.surfaceMuted, borderColor: colors.primary },
    hr: { backgroundColor: colors.border },
    table: { borderColor: colors.border },
    tr: { borderColor: colors.border },
  });
