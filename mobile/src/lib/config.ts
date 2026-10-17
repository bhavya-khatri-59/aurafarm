/**
 * Backend URL. Set EXPO_PUBLIC_API_URL in mobile/.env (e.g. http://192.168.1.20:8000 for a phone on
 * your Wi-Fi). The default reaches a backend on your computer from the Android emulator.
 */
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://10.0.2.2:8000').replace(/\/$/, '');
