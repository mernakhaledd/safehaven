import { Platform } from 'react-native';

import * as SecureStore from 'expo-secure-store';

function getWebStorage(): Storage | null {
  // In some environments (SSR / restricted contexts), localStorage may be unavailable.
  if (typeof window === 'undefined') return null;
  return window.localStorage ?? null;
}

export const secureStore = {
  async getItem(key: string): Promise<string | null> {
    if (Platform.OS === 'web') {
      return getWebStorage()?.getItem(key) ?? null;
    }
    return await SecureStore.getItemAsync(key);
  },
  async setItem(key: string, value: string): Promise<void> {
    if (Platform.OS === 'web') {
      getWebStorage()?.setItem(key, value);
      return;
    }
    await SecureStore.setItemAsync(key, value);
  },
  async removeItem(key: string): Promise<void> {
    if (Platform.OS === 'web') {
      getWebStorage()?.removeItem(key);
      return;
    }
    await SecureStore.deleteItemAsync(key);
  },
};

