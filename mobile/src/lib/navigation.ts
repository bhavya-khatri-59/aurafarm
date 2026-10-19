import { router } from 'expo-router';

/** Opens a conversation (or a blank new chat when id is omitted) from anywhere in the app. */
export function openConversation(id?: string) {
  router.navigate({ pathname: '/', params: { id: id ?? '' } });
}
