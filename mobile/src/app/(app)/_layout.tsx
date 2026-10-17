import { Ionicons } from '@expo/vector-icons';
import { router, useGlobalSearchParams } from 'expo-router';
import { Drawer } from 'expo-router/drawer';
import { Pressable } from 'react-native';

import { ConversationDrawer } from '@/components/ConversationDrawer';
import { ConversationsProvider, useConversations } from '@/lib/conversations';
import { colors } from '@/theme';

function AppDrawer() {
  const { id } = useGlobalSearchParams<{ id?: string }>();
  const { conversations } = useConversations();
  const title = conversations.find((c) => c.id === id)?.title ?? 'New conversation';

  return (
    <Drawer
      drawerContent={(props) => <ConversationDrawer {...props} />}
      screenOptions={{
        headerTintColor: colors.text,
        headerStyle: { backgroundColor: colors.surface },
        headerTitleStyle: { fontSize: 17, fontWeight: '600' },
        drawerStyle: { width: 300 },
        headerRight: () => (
          <Pressable
            onPress={() => router.setParams({ id: undefined })}
            hitSlop={12}
            style={{ marginRight: 16 }}
            accessibilityLabel="New conversation"
          >
            <Ionicons name="create-outline" size={24} color={colors.primary} />
          </Pressable>
        ),
      }}
    >
      <Drawer.Screen name="index" options={{ title }} />
    </Drawer>
  );
}

export default function AppLayout() {
  return (
    <ConversationsProvider>
      <AppDrawer />
    </ConversationsProvider>
  );
}
