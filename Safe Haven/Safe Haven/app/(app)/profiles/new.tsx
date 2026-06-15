import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { Button } from '../../../src/components/ui/Button';
import { Card } from '../../../src/components/ui/Card';
import { Screen } from '../../../src/components/ui/Screen';
import { useAuth } from '../../../src/providers/AuthProvider';
import type { Persona, ReceiverType } from '../../../src/providers/ProfileProvider';
import { useProfile } from '../../../src/providers/ProfileProvider';
import { supabase } from '../../../src/lib/supabase';
import { Colors } from '../../../src/theme/colors';

export default function NewProfileScreen() {
  const [displayName, setDisplayName] = useState('');
  const [persona, setPersona] = useState<Persona>('care_giver');
  const [receiverType, setReceiverType] = useState<ReceiverType>('adult');
  const { session } = useAuth();
  const { refreshProfiles } = useProfile();

  async function onCreate() {
    if (!displayName.trim()) {
      Alert.alert('Missing name', 'Please enter a profile name.');
      return;
    }

    if (!session) {
      Alert.alert('Not signed in', 'Please sign in again.');
      router.replace('/(auth)/sign-in');
      return;
    }

    const { error } = await supabase.from('profiles').insert({
      user_id: session.user.id,
      display_name: displayName.trim(),
      persona,
      receiver_type: persona === 'care_receiver' ? receiverType : null,
    });

    if (error) {
      Alert.alert('Create failed', error.message);
      return;
    }

    await refreshProfiles();
    router.back();
  }

  return (
    <Screen>
      <Text style={styles.title}>Create profile</Text>
      <Text style={styles.subtitle}>Choose a name, persona, and receiver type.</Text>

      <Card style={styles.card}>
        <Text style={styles.label}>Profile name</Text>
        <TextInput
          style={styles.input}
          value={displayName}
          onChangeText={setDisplayName}
          placeholder="e.g., Dad, Grandma, Alex"
        />

        <View style={{ height: 14 }} />

        <Text style={styles.label}>Persona</Text>
        <View style={styles.pillsRow}>
          <Pill
            title="Care Giver"
            isActive={persona === 'care_giver'}
            onPress={() => setPersona('care_giver')}
          />
          <Pill
            title="Care Receiver"
            isActive={persona === 'care_receiver'}
            onPress={() => setPersona('care_receiver')}
          />
        </View>

        {persona === 'care_receiver' ? (
          <>
            <View style={{ height: 14 }} />
            <Text style={styles.label}>Receiver type</Text>
            <View style={styles.pillsRow}>
              {(['infant', 'toddler', 'teen', 'adult', 'elder'] as ReceiverType[]).map((t) => (
                <Pill key={t} title={t} isActive={receiverType === t} onPress={() => setReceiverType(t)} />
              ))}
            </View>
          </>
        ) : null}
      </Card>

      <Button title="Create" onPress={onCreate} />
      <View style={{ height: 10 }} />
      <Button title="Cancel" variant="ghost" onPress={() => router.back()} />
    </Screen>
  );
}

function Pill({
  title,
  isActive,
  onPress,
}: {
  title: string;
  isActive: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable onPress={onPress} style={[styles.pill, isActive && styles.pillActive]}>
      <Text style={[styles.pillText, isActive && styles.pillTextActive]}>{title}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 26, fontWeight: '800', color: Colors.text },
  subtitle: { marginTop: 6, marginBottom: 16, color: Colors.muted },
  card: {
    marginBottom: 16,
  },
  label: { fontSize: 13, fontWeight: '800', color: Colors.muted, marginBottom: 6 },
  input: {
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.white,
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 12,
    fontSize: 16,
    color: Colors.text,
  },
  pillsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  pill: {
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.bg,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 999,
  },
  pillActive: {
    borderColor: Colors.primary,
    backgroundColor: 'rgba(10,132,255,0.10)',
  },
  pillText: { color: Colors.text, fontWeight: '800' },
  pillTextActive: { color: Colors.primaryDark },
});
