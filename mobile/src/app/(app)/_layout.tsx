import { Ionicons } from '@expo/vector-icons';
import { useGlobalSearchParams } from 'expo-router';
import { Drawer } from 'expo-router/drawer';
import { Pressable } from 'react-native';

import { ConversationDrawer } from '@/components/ConversationDrawer';
import { ConversationsProvider, useConversations } from '@/lib/conversations';
import { openConversation } from '@/lib/navigation';
import { useTheme } from '@/lib/theme';

function AppDrawer() {
  const { id } = useGlobalSearchParams<{ id?: string }>();
  const { conversations } = useConversations();
  const { colors } = useTheme();
  const title = conversations.find((c) => c.id === id)?.title ?? 'New conversation';

  return (
    <Drawer
      drawerContent={(props) => <ConversationDrawer {...props} />}
      screenOptions={{
        headerTintColor: colors.text,
        headerStyle: { backgroundColor: colors.surface },
        headerShadowVisible: false,
        headerTitleStyle: { fontSize: 17, fontWeight: '600', color: colors.text },
        drawerStyle: { width: 304, backgroundColor: colors.background },
        sceneStyle: { backgroundColor: colors.background },
      }}
    >
      <Drawer.Screen
        name="index"
        options={{
          title,
          headerRight: () => (
            <Pressable
              onPress={() => openConversation()}
              hitSlop={12}
              style={{ marginRight: 16 }}
              accessibilityLabel="New conversation"
            >
              <Ionicons name="create-outline" size={24} color={colors.primary} />
            </Pressable>
          ),
        }}
      />
      <Drawer.Screen name="settings" options={{ title: 'Settings' }} />
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
