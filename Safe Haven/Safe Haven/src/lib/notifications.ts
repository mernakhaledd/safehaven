// Push notification plumbing: permissions, token retrieval, and saving the
// token to Supabase so the backend (send_push) can reach this device even
// when the app/phone is closed.
//
// NOTE: real push only works in a real build (APK / store build), NOT in
// Expo Go. In Expo Go these calls fail gracefully and do nothing.

import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';
import { Platform } from 'react-native';

import { supabase } from './supabase';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export async function requestPushPermissionsIfNeeded(): Promise<boolean> {
  const current = await Notifications.getPermissionsAsync();
  if (current.granted) return true;
  const req = await Notifications.requestPermissionsAsync();
  return req.granted;
}

export async function getExpoPushTokenAsync(): Promise<string | null> {
  const granted = await requestPushPermissionsIfNeeded();
  if (!granted) return null;

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'SafeHaven Alerts',
      importance: Notifications.AndroidImportance.MAX,
      sound: 'default',
    });
  }

  // projectId is required to get an Expo push token in a real build (SDK 53+)
  const projectId =
    (Constants?.expoConfig as any)?.extra?.eas?.projectId ??
    (Constants as any)?.easConfig?.projectId;

  const token = await Notifications.getExpoPushTokenAsync(
    projectId ? { projectId } : undefined,
  );
  return token.data ?? null;
}

/**
 * Get this device's push token and save it to Supabase for the given user,
 * so the backend can push alerts to it. Safe to call repeatedly; no-ops in
 * Expo Go or if permission is denied.
 */
export async function registerPushTokenForSession(userId: string): Promise<void> {
  try {
    const token = await getExpoPushTokenAsync();
    if (!token) return;
    await supabase
      .from('device_push_tokens')
      .upsert(
        {
          user_id: userId,
          expo_push_token: token,
          platform: Platform.OS,
          updated_at: new Date().toISOString(),
        },
        { onConflict: 'expo_push_token' },
      );
  } catch (e) {
    // Expected in Expo Go / when push isn't available; not fatal.
    console.warn('[push] token registration skipped:', e);
  }
}
