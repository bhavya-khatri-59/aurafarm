import { Ionicons } from '@expo/vector-icons';
import { router, useGlobalSearchParams } from 'expo-router';
import type { DrawerContentComponentProps } from 'expo-router/drawer';
import { useState } from 'react';
import { ActivityIndicator, Alert, FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { RenameModal } from './RenameModal';
import { useAuth } from '@/lib/auth';
import { useConversations } from '@/lib/conversations';
import type { Conversation } from '@/lib/types';
import { colors, radius } from '@/theme';

function relativeDay(iso: string): string {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  return new Date(iso).toLocaleDateString();
}

export function ConversationDrawer({ navigation }: DrawerContentComponentProps) {
  const { id: activeId } = useGlobalSearchParams<{ id?: string }>();
  const { conversations, isLoading, rename, remove } = useConversations();
  const { user, signOut } = useAuth();
  const [renaming, setRenaming] = useState<Conversation | null>(null);

  const open = (id?: string) => {
    router.setParams({ id });
    navigation.closeDrawer();
  };

  const showActions = (conversation: Conversation) =>
    Alert.alert(conversation.title, undefined, [
      { text: 'Rename', onPress: () => setRenaming(conversation) },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: () =>
          Alert.alert('Delete conversation?', 'This cannot be undone.', [
            { text: 'Cancel', style: 'cancel' },
            {
              text: 'Delete',
              style: 'destructive',
              onPress: async () => {
                await remove(conversation.id).catch((e) => Alert.alert('Could not delete', e.message));
                if (conversation.id === activeId) open(undefined);
              },
            },
          ]),
      },
      { text: 'Cancel', style: 'cancel' },
    ]);

  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom', 'left']}>
      <Text style={styles.brand}>AuraFarm</Text>
      <Pressable style={styles.newButton} onPress={() => open(undefined)}>
        <Ionicons name="add" size={20} color="#fff" />
        <Text style={styles.newButtonText}>New conversation</Text>
      </Pressable>

      {isLoading ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: 24 }} />
      ) : (
        <FlatList
          data={conversations}
          keyExtractor={(c) => c.id}
          contentContainerStyle={{ paddingVertical: 8 }}
          ListEmptyComponent={<Text style={styles.empty}>Your conversations will appear here.</Text>}
          renderItem={({ item }) => (
            <Pressable
              style={[styles.item, item.id === activeId && styles.itemActive]}
              onPress={() => open(item.id)}
              onLongPress={() => showActions(item)}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.itemTitle} numberOfLines={1}>
                  {item.title}
                </Text>
                <Text style={styles.itemDate}>{relativeDay(item.updated_at)}</Text>
              </View>
              <Pressable hitSlop={10} onPress={() => showActions(item)} accessibilityLabel="Conversation options">
                <Ionicons name="ellipsis-horizontal" size={18} color={colors.textMuted} />
              </Pressable>
            </Pressable>
          )}
        />
      )}

      <View style={styles.footer}>
        <Ionicons name="person-circle-outline" size={28} color={colors.textMuted} />
        <Text style={styles.userName} numberOfLines={1}>
          {user?.name}
        </Text>
        <Pressable onPress={signOut} hitSlop={10}>
          <Text style={styles.signOut}>Sign out</Text>
        </Pressable>
      </View>

      <RenameModal
        visible={renaming !== null}
        initialTitle={renaming?.title ?? ''}
        onCancel={() => setRenaming(null)}
        onSave={async (title) => {
          const target = renaming;
          setRenaming(null);
          if (target) await rename(target.id, title).catch((e) => Alert.alert('Could not rename', e.message));
        }}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background, paddingHorizontal: 12 },
  brand: { fontSize: 22, fontWeight: '700', color: colors.primaryDark, marginTop: 12, marginBottom: 16, marginLeft: 4 },
  newButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: colors.primary,
    borderRadius: radius.sm,
    paddingVertical: 12,
    paddingHorizontal: 14,
  },
  newButtonText: { color: '#fff', fontWeight: '600', fontSize: 15 },
  empty: { color: colors.textMuted, textAlign: 'center', marginTop: 24 },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 10,
    borderRadius: radius.sm,
    marginVertical: 1,
  },
  itemActive: { backgroundColor: colors.primarySoft },
  itemTitle: { fontSize: 15, color: colors.text },
  itemDate: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    paddingVertical: 12,
    paddingHorizontal: 4,
  },
  userName: { flex: 1, color: colors.text, fontSize: 15 },
  signOut: { color: colors.danger, fontWeight: '600' },
});
