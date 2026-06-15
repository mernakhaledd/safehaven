// Minimal notification plumbing for now (Expo push token retrieval + permission prompt)
// We'll later store tokens in Supabase and send notifications from Edge Functions.

import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: false,
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

  // Android requires a channel for notifications shown while app is foreground/background.
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'default',
      importance: Notifications.AndroidImportance.DEFAULT,
    });
  }

  const token = await Notifications.getExpoPushTokenAsync();
  return token.data ?? null;
}

