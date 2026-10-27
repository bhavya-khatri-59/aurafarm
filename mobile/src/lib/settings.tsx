import * as SecureStore from 'expo-secure-store';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

const DEMO_MODE_KEY = 'aurafarm.demoMode';

type SettingsContextValue = {
  /** Photos are answered only from the server's saved replies; no AI calls. */
  demoMode: boolean;
  setDemoMode: (on: boolean) => void;
};

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [demoMode, setDemoModeState] = useState(false);

  useEffect(() => {
    SecureStore.getItemAsync(DEMO_MODE_KEY)
      .then((saved) => setDemoModeState(saved === 'true'))
      .catch(() => {});
  }, []);

  const setDemoMode = useCallback((on: boolean) => {
    setDemoModeState(on);
    SecureStore.setItemAsync(DEMO_MODE_KEY, String(on)).catch(() => {});
  }, []);

  const value = useMemo(() => ({ demoMode, setDemoMode }), [demoMode, setDemoMode]);
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (!context) throw new Error('useSettings must be used inside SettingsProvider');
  return context;
}
