import { router } from 'expo-router';
import { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  StyleSheet,
  Text,
  View,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import type { Profile } from '../../../src/providers/ProfileProvider';
import { useProfile } from '../../../src/providers/ProfileProvider';
import { Button } from '../../../src/components/ui/Button';
import { Colors } from '../../../src/theme/colors';
import { supabase } from '../../../src/lib/supabase';

export default function ProfilesScreen() {
  const { isLoading, profiles, setActiveProfile, refreshProfiles } = useProfile();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  function confirmDelete(p: Profile) {
    const yes = window.confirm(`Delete profile "${p.displayName}"?\n\nThis will permanently remove the profile and all its linked data.`);
    if (yes) doDelete(p);
  }

  async function doDelete(p: Profile) {
    setDeletingId(p.id);
    try {
      const { error } = await supabase.rpc('delete_profile', { p_profile_id: p.id });
      if (error) {
        window.alert('Delete failed: ' + error.message);
      } else {
        await refreshProfiles();
      }
    } catch (e) {
      window.alert('Error: ' + (e instanceof Error ? e.message : 'Failed to delete.'));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.title}>Who's using Safe Haven?</Text>
        <Text style={styles.subtitle}>Select a profile</Text>

        {isLoading ? (
          <View style={{ paddingTop: 18 }}>
            <ActivityIndicator />
          </View>
        ) : (
          <>
            <View style={styles.grid}>
              {profiles.map((p: Profile) => (
                <View key={p.id} style={styles.card}>
                  {/* Top row: persona label + delete button */}
                  <View style={styles.cardTopRow}>
                    <Text style={styles.meta}>
                      {p.persona === 'care_giver'
                        ? 'Care Giver'
                        : `Care Receiver • ${p.receiverType ?? 'adult'}`}
                    </Text>

                    <Pressable
                      onPress={() => confirmDelete(p)}
                      disabled={deletingId === p.id}
                      style={({ pressed }) => [
                        styles.deleteBtn,
                        pressed && { opacity: 0.6 },
                      ]}
                    >
                      {deletingId === p.id ? (
                        <ActivityIndicator size="small" color={Colors.danger} />
                      ) : (
                        <Ionicons name="trash-outline" size={18} color={Colors.danger} />
                      )}
                    </Pressable>
                  </View>

                  {/* Profile name — tappable to select */}
                  <Pressable
                    style={({ pressed }) => [pressed && { opacity: 0.7 }]}
                    onPress={() => {
                      setActiveProfile(p);
                      router.replace(
                        p.persona === 'care_giver'
                          ? '/(app)/caregiver/home'
                          : '/(app)/receiver/home',
                      );
                    }}
                  >
                    <Text style={styles.name}>{p.displayName}</Text>
                    <Text style={styles.selectHint}>Tap to select</Text>
                  </Pressable>
                </View>
              ))}
            </View>

            {profiles.length === 0 ? (
              <View style={styles.empty}>
                <Text style={styles.emptyTitle}>No profiles yet</Text>
                <Text style={styles.emptyBody}>
                  Create a Care Giver or Care Receiver profile to customize the app experience.
                </Text>
              </View>
            ) : null}
          </>
        )}

        <View style={{ height: 18 }} />
        <Button
          title="Create profile"
          variant="secondary"
          onPress={() => router.push('/(app)/profiles/new')}
        />
        <View style={{ height: 10 }} />
        <Button title="Refresh" variant="ghost" onPress={refreshProfiles} />
        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  title: { fontSize: 26, fontWeight: '800', letterSpacing: -0.3 },
  subtitle: { marginTop: 6, marginBottom: 18, color: '#5B667A' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 14 },

  card: {
    width: '48%',
    minHeight: 110,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: '#eee',
    backgroundColor: '#fafafa',
    padding: 14,
    gap: 10,
  },
  cardTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  deleteBtn: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: '#FFF0F0',
  },

  name: { fontSize: 18, fontWeight: '700' },
  meta: { color: '#666', fontSize: 12, flex: 1, marginRight: 8 },
  selectHint: { color: Colors.primary, fontSize: 11, fontWeight: '600', marginTop: 4 },

  empty: {
    marginTop: 18,
    backgroundColor: Colors.card,
    borderColor: Colors.border,
    borderWidth: 1,
    borderRadius: 18,
    padding: 16,
  },
  emptyTitle: { fontWeight: '900', color: Colors.text, marginBottom: 6 },
  emptyBody: { color: Colors.muted, lineHeight: 20 },
  scrollContent: { padding: 20 },
});
