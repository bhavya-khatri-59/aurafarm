import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { api } from './api';
import type { Conversation } from './types';

type ConversationsContextValue = {
  conversations: Conversation[];
  isLoading: boolean;
  refresh: () => Promise<void>;
  /** Inserts or updates a conversation and moves it to the top of the list. */
  touch: (conversation: Conversation) => void;
  rename: (id: string, title: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
};

const ConversationsContext = createContext<ConversationsContextValue | null>(null);

export function ConversationsProvider({ children }: { children: ReactNode }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setConversations(await api.listConversations());
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  const touch = useCallback((conversation: Conversation) => {
    setConversations((current) => [conversation, ...current.filter((c) => c.id !== conversation.id)]);
  }, []);

  const rename = useCallback(async (id: string, title: string) => {
    const updated = await api.renameConversation(id, title);
    setConversations((current) => current.map((c) => (c.id === id ? updated : c)));
  }, []);

  const remove = useCallback(async (id: string) => {
    await api.deleteConversation(id);
    setConversations((current) => current.filter((c) => c.id !== id));
  }, []);

  const value = useMemo(
    () => ({ conversations, isLoading, refresh, touch, rename, remove }),
    [conversations, isLoading, refresh, touch, rename, remove],
  );
  return <ConversationsContext.Provider value={value}>{children}</ConversationsContext.Provider>;
}

export function useConversations() {
  const context = useContext(ConversationsContext);
  if (!context) throw new Error('useConversations must be used inside ConversationsProvider');
  return context;
}
