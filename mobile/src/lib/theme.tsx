import * as SecureStore from 'expo-secure-store';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';

import { darkColors, lightColors, type Colors } from '@/theme';

export type ThemePreference = 'system' | 'light' | 'dark';

const PREFERENCE_KEY = 'aurafarm.theme';

type ThemeContextValue = {
  colors: Colors;
  isDark: boolean;
  preference: ThemePreference;
  setPreference: (preference: ThemePreference) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const systemScheme = useColorScheme();
  const [preference, setPreferenceState] = useState<ThemePreference>('system');

  useEffect(() => {
    SecureStore.getItemAsync(PREFERENCE_KEY)
      .then((saved) => {
        if (saved === 'light' || saved === 'dark' || saved === 'system') setPreferenceState(saved);
      })
      .catch(() => {});
  }, []);

  const setPreference = useCallback((next: ThemePreference) => {
    setPreferenceState(next);
    SecureStore.setItemAsync(PREFERENCE_KEY, next).catch(() => {});
  }, []);

  const isDark = preference === 'dark' || (preference === 'system' && systemScheme === 'dark');
  const value = useMemo(
    () => ({ colors: isDark ? darkColors : lightColors, isDark, preference, setPreference }),
    [isDark, preference, setPreference],
  );
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used inside ThemeProvider');
  return context;
}

/** Memoized styles that follow the active theme: `const styles = useThemedStyles(makeStyles)`. */
export function useThemedStyles<T>(factory: (colors: Colors) => T): T {
  const { colors } = useTheme();
  return useMemo(() => factory(colors), [colors, factory]);
}
