import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Composer, type PickedImage } from './Composer';
import { MessageBubble, type ChatItem } from './MessageBubble';
import { api } from '@/lib/api';
import { useConversations } from '@/lib/conversations';
import { getCoords } from '@/lib/location';
import type { Message } from '@/lib/types';
import { colors, radius } from '@/theme';

const SUGGESTIONS = [
  'How do I prevent late blight on tomatoes?',
  'What should I spray for powdery mildew on squash?',
  'Where can I buy farm supplies near me?',
];

const toItem = (m: Message): ChatItem => ({
  key: `m${m.id}`,
  role: m.role,
  content: m.content,
  imageId: m.image_id,
  diagnosis: m.diagnosis,
});

export function ChatScreen({ conversationId }: { conversationId: string | null }) {
  const insets = useSafeAreaInsets();
  const { touch, refresh } = useConversations();
  const [items, setItems] = useState<ChatItem[]>([]);
  const [text, setText] = useState('');
  const [image, setImage] = useState<PickedImage | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  // The conversation currently shown. Kept in a ref so that when a new conversation is created
  // mid-send and the route param changes to its id, we don't reload over the live stream.
  const shownIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (conversationId === shownIdRef.current) return;
    abortRef.current?.abort();
    shownIdRef.current = conversationId;
    setItems([]);
    setLoadError(null);
    setSending(false);
    if (!conversationId) return;

    let cancelled = false;
    setLoading(true);
    api
      .getConversation(conversationId)
      .then((detail) => !cancelled && setItems(detail.messages.map(toItem)))
      .catch((e) => !cancelled && setLoadError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const updateItem = useCallback((key: string, patch: (item: ChatItem) => Partial<ChatItem>) => {
    setItems((current) => current.map((item) => (item.key === key ? { ...item, ...patch(item) } : item)));
  }, []);

  const send = useCallback(
    async (overrideText?: string) => {
      const messageText = (overrideText ?? text).trim();
      const messageImage = overrideText ? null : image;
      if (sending || (!messageText && !messageImage)) return;

      setText('');
      setImage(null);
      setSending(true);
      const stamp = Date.now();
      const userKey = `local-user-${stamp}`;
      const replyKey = `local-reply-${stamp}`;
      setItems((current) => [
        ...current,
        { key: userKey, role: 'user', content: messageText, localImageUri: messageImage?.uri },
        { key: replyKey, role: 'assistant', content: '', pending: true, status: null },
      ]);

      const abort = new AbortController();
      abortRef.current = abort;
      try {
        let id = shownIdRef.current;
        if (!id) {
          const conversation = await api.createConversation();
          id = conversation.id;
          shownIdRef.current = id;
          touch(conversation);
          router.setParams({ id });
        }
        const [imageId, coords] = await Promise.all([
          messageImage ? api.uploadImage(messageImage.uri, messageImage.mimeType) : Promise.resolve(null),
          getCoords(),
        ]);

        await api.sendMessage(
          id,
          { text: messageText, image_id: imageId, ...(coords ?? {}) },
          ({ event, data }) => {
            if (abort.signal.aborted) return;
            switch (event) {
              case 'status':
                updateItem(replyKey, () => ({ status: data.text }));
                break;
              case 'diagnosis':
                updateItem(replyKey, () => ({ diagnosis: data }));
                break;
              case 'reset':
                updateItem(replyKey, () => ({ content: '' }));
                break;
              case 'token':
                updateItem(replyKey, (item) => ({ content: item.content + data.text, status: null }));
                break;
              case 'message':
                updateItem(replyKey, () => ({ key: `m${data.id}`, content: data.content, pending: false, status: null }));
                break;
              case 'done':
                refresh().catch(() => {});
                break;
              case 'error':
                updateItem(replyKey, () => ({ pending: false, status: null, error: data.detail }));
                break;
            }
          },
          abort.signal,
        );
      } catch (e) {
        if (!abort.signal.aborted) {
          const message = e instanceof Error ? e.message : 'Something went wrong. Please try again.';
          updateItem(replyKey, () => ({ pending: false, status: null, error: message }));
        }
      } finally {
        if (abortRef.current === abort) {
          setSending(false);
          // If the stream ended without a final message, stop the spinner.
          updateItem(replyKey, () => ({ pending: false, status: null }));
        }
      }
    },
    [text, image, sending, touch, refresh, updateItem],
  );

  const empty = !loading && items.length === 0;

  return (
    <KeyboardAvoidingView
      style={[styles.container, { paddingBottom: insets.bottom }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      {loading ? (
        <ActivityIndicator color={colors.primary} style={{ flex: 1 }} />
      ) : loadError ? (
        <View style={styles.center}>
          <Text style={styles.errorText}>{loadError}</Text>
        </View>
      ) : empty ? (
        <View style={styles.center}>
          <Image source={require('../../assets/logo.png')} style={styles.logo} contentFit="contain" />
          <Text style={styles.welcome}>How are your plants today?</Text>
          <Text style={styles.welcomeSub}>
            Send a photo of a leaf to diagnose a disease, or ask anything about your crops.
          </Text>
          <View style={styles.suggestions}>
            {SUGGESTIONS.map((s) => (
              <Pressable key={s} style={styles.suggestion} onPress={() => send(s)}>
                <Text style={styles.suggestionText}>{s}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      ) : (
        <FlatList
          data={[...items].reverse()}
          inverted
          keyExtractor={(item) => item.key}
          renderItem={({ item }) => <MessageBubble item={item} />}
          contentContainerStyle={{ paddingVertical: 12 }}
          keyboardDismissMode="interactive"
        />
      )}
      <Composer
        text={text}
        onChangeText={setText}
        image={image}
        onChangeImage={setImage}
        onSend={() => send()}
        disabled={sending}
      />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  logo: { width: 64, height: 64, marginBottom: 12 },
  welcome: { fontSize: 22, fontWeight: '700', color: colors.text },
  welcomeSub: { fontSize: 15, color: colors.textMuted, textAlign: 'center', marginTop: 6, maxWidth: 320 },
  suggestions: { marginTop: 24, gap: 8, alignSelf: 'stretch' },
  suggestion: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingVertical: 12,
    paddingHorizontal: 14,
  },
  suggestionText: { color: colors.text, fontSize: 15 },
  errorText: { color: colors.danger, textAlign: 'center' },
});
