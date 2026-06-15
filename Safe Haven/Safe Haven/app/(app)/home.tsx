import { Link, router } from 'expo-router';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { supabase } from '../../src/lib/supabase';
import { getExpoPushTokenAsync } from '../../src/lib/notifications';
import { useProfile } from '../../src/providers/ProfileProvider';

export default function HomeScreen() {
  const { activeProfile } = useProfile();

  async function onSignOut() {
    const { error } = await supabase.auth.signOut();
    if (error) {
      Alert.alert('Sign out failed', error.message);
      return;
    }
    router.replace('/(auth)/sign-in');
  }

  async function onGetPushToken() {
    try {
      const token = await getExpoPushTokenAsync();
      Alert.alert('Expo push token', token ?? 'Permission denied');
    } catch (e) {
      Alert.alert('Push setup failed', e instanceof Error ? e.message : 'Unknown error');
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Home</Text>
      <Text style={styles.subtitle}>
        Active profile: {activeProfile ? `${activeProfile.displayName} (${activeProfile.persona})` : 'none'}
      </Text>
      <Text style={styles.subtitle}>
        Next: persona-based dashboard (Care Giver vs Care Receiver).
      </Text>

      <View style={styles.row}>
        <Link href="/(app)/profiles" style={styles.link}>
          Go to Profiles
        </Link>
        <Link href="/(app)/notifications" style={[styles.link, { fontSize: 20, color: '#ff3b30' }]}>
          View ALERTS (Integration Live)
        </Link>

        <Pressable onPress={onSignOut} style={styles.secondaryButton}>
          <Text style={styles.secondaryButtonText}>Sign out</Text>
        </Pressable>

        <Pressable onPress={onGetPushToken} style={styles.secondaryButton}>
          <Text style={styles.secondaryButtonText}>Get push token</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', padding: 20 },
  title: { fontSize: 28, fontWeight: '700', marginBottom: 8 },
  subtitle: { color: '#555', marginBottom: 16 },
  row: { gap: 12 },
  link: { color: '#0A84FF', fontSize: 16, fontWeight: '600' },
  secondaryButton: {
    alignSelf: 'flex-start',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e6e6e6',
    backgroundColor: '#fff',
  },
  secondaryButtonText: { fontWeight: '700' },
});

