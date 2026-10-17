import * as SecureStore from 'expo-secure-store';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { api, setAuthToken, setUnauthorizedHandler } from './api';
import type { User } from './types';

const TOKEN_KEY = 'aurafarm.token';

type AuthContextValue = {
  user: User | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, name: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const signOut = useCallback(async () => {
    setAuthToken(null);
    setUser(null);
    await SecureStore.deleteItemAsync(TOKEN_KEY);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => void signOut());
    (async () => {
      const token = await SecureStore.getItemAsync(TOKEN_KEY);
      if (token) {
        setAuthToken(token);
        try {
          setUser(await api.me());
        } catch {
          // Token expired or server unreachable: send the user to sign in.
          setAuthToken(null);
        }
      }
      setIsLoading(false);
    })();
    return () => setUnauthorizedHandler(null);
  }, [signOut]);

  const finishAuth = useCallback(async ({ access_token, user }: { access_token: string; user: User }) => {
    setAuthToken(access_token);
    await SecureStore.setItemAsync(TOKEN_KEY, access_token);
    setUser(user);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      signIn: async (email, password) => finishAuth(await api.login(email, password)),
      signUp: async (email, name, password) => finishAuth(await api.register(email, name, password)),
      signOut,
    }),
    [user, isLoading, finishAuth, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
