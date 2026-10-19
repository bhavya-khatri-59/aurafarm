import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import { router, useGlobalSearchParams, usePathname } from 'expo-router';
import type { DrawerContentComponentProps } from 'expo-router/drawer';
import { useState } from 'react';
import { ActivityIndicator, Alert, FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { RenameModal } from './RenameModal';
import { useAuth } from '@/lib/auth';
import { useConversations } from '@/lib/conversations';
import { openConversation } from '@/lib/navigation';
import { useTheme, useThemedStyles } from '@/lib/theme';
import type { Conversation } from '@/lib/types';
import { radius, type Colors } from '@/theme';

function relativeDay(iso: string): string {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  return new Date(iso).toLocaleDateString();
}

export function ConversationDrawer({ navigation }: DrawerContentComponentProps) {
  const { id } = useGlobalSearchParams<{ id?: string }>();
  const pathname = usePathname();
  const activeId = pathname === '/' ? id : undefined;
  const { conversations, isLoading, rename, remove } = useConversations();
  const { user } = useAuth();
  const { colors } = useTheme();
  const styles = useThemedStyles(makeStyles);
  const [renaming, setRenaming] = useState<Conversation | null>(null);

  const open = (conversationId?: string) => {
    openConversation(conversationId);
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
      <View style={styles.brandRow}>
        <Image source={require('../../assets/logo.png')} style={styles.logo} contentFit="contain" />
        <Text style={styles.brand}>AuraFarm</Text>
      </View>

      <Pressable style={styles.newButton} onPress={() => open(undefined)}>
        <Ionicons name="add" size={20} color={colors.onPrimary} />
        <Text style={styles.newButtonText}>New conversation</Text>
      </Pressable>

      <Text style={styles.sectionLabel}>Conversations</Text>
      {isLoading ? (
        <ActivityIndicator color={colors.primary} style={{ marginTop: 24 }} />
      ) : (
        <FlatList
          data={conversations}
          keyExtractor={(c) => c.id}
          contentContainerStyle={{ paddingBottom: 8 }}
          ListEmptyComponent={<Text style={styles.empty}>Your conversations will appear here.</Text>}
          renderItem={({ item }) => {
            const active = item.id === activeId;
            return (
              <Pressable
                style={({ pressed }) => [
                  styles.item,
                  active && styles.itemActive,
                  pressed && !active && styles.itemPressed,
                ]}
                onPress={() => open(item.id)}
                onLongPress={() => showActions(item)}
              >
                <Ionicons
                  name={active ? 'chatbubble' : 'chatbubble-outline'}
                  size={16}
                  color={active ? colors.primary : colors.textMuted}
                />
                <View style={{ flex: 1 }}>
                  <Text style={[styles.itemTitle, active && styles.itemTitleActive]} numberOfLines={1}>
                    {item.title}
                  </Text>
                  <Text style={styles.itemDate}>{relativeDay(item.updated_at)}</Text>
                </View>
                <Pressable hitSlop={10} onPress={() => showActions(item)} accessibilityLabel="Conversation options">
                  <Ionicons name="ellipsis-horizontal" size={18} color={colors.textMuted} />
                </Pressable>
              </Pressable>
            );
          }}
        />
      )}

      <Pressable
        style={({ pressed }) => [styles.footer, pressed && { opacity: 0.7 }]}
        onPress={() => {
          router.navigate('/settings');
          navigation.closeDrawer();
        }}
      >
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{user?.name?.[0]?.toUpperCase() ?? '?'}</Text>
        </View>
        <Text style={styles.userName} numberOfLines={1}>
          {user?.name}
        </Text>
        <Ionicons name="settings-outline" size={20} color={colors.textMuted} />
      </Pressable>

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

const makeStyles = (colors: Colors) =>
  StyleSheet.create({
    container: { flex: 1, backgroundColor: colors.background, paddingHorizontal: 12 },
    brandRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 12, marginBottom: 18, marginLeft: 4 },
    logo: { width: 30, height: 30 },
    brand: { fontSize: 22, fontWeight: '700', color: colors.primaryStrong, letterSpacing: 0.2 },
    newButton: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      backgroundColor: colors.primary,
      borderRadius: radius.md,
      paddingVertical: 12,
    },
    newButtonText: { color: colors.onPrimary, fontWeight: '600', fontSize: 15 },
    sectionLabel: {
      fontSize: 12,
      fontWeight: '600',
      color: colors.textMuted,
      textTransform: 'uppercase',
      letterSpacing: 0.6,
      marginTop: 22,
      marginBottom: 6,
      marginLeft: 6,
    },
    empty: { color: colors.textMuted, textAlign: 'center', marginTop: 24 },
    item: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 10,
      paddingVertical: 10,
      paddingHorizontal: 10,
      borderRadius: radius.sm,
      marginVertical: 1,
    },
    itemActive: { backgroundColor: colors.primarySoft },
    itemPressed: { backgroundColor: colors.surfaceMuted },
    itemTitle: { fontSize: 15, color: colors.text },
    itemTitleActive: { fontWeight: '600' },
    itemDate: { fontSize: 12, color: colors.textMuted, marginTop: 2 },
    footer: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 10,
      borderTopWidth: StyleSheet.hairlineWidth,
      borderTopColor: colors.border,
      paddingVertical: 12,
      paddingHorizontal: 4,
    },
    avatar: {
      width: 32,
      height: 32,
      borderRadius: 16,
      backgroundColor: colors.primarySoft,
      alignItems: 'center',
      justifyContent: 'center',
    },
    avatarText: { color: colors.primary, fontWeight: '700', fontSize: 15 },
    userName: { flex: 1, color: colors.text, fontSize: 15, fontWeight: '500' },
  });
