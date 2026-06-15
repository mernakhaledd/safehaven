import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';

import { Button } from '../../../src/components/ui/Button';
import { Colors } from '../../../src/theme/colors';
import { useAuth } from '../../../src/providers/AuthProvider';
import { supabase } from '../../../src/lib/supabase';

type FamilyMember = {
  id: string;
  display_name: string;
  member_photos: { status: string }[];
};

function confirmDialog(message: string, onYes: () => void) {
  if (Platform.OS === 'web') {
    // eslint-disable-next-line no-alert
    if (window.confirm(message)) onYes();
  } else {
    Alert.alert('Confirm', message, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: onYes },
    ]);
  }
}

function notify(title: string, message: string) {
  if (Platform.OS === 'web') {
    // eslint-disable-next-line no-alert
    window.alert(`${title}\n\n${message}`);
  } else {
    Alert.alert(title, message);
  }
}

function base64ToBytes(b64: string): Uint8Array {
  const clean = b64.includes(',') ? b64.split(',')[1] : b64;
  const bin = atob(clean);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

export default function FamilyScreen() {
  const { session } = useAuth();
  const [members, setMembers] = useState<FamilyMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState('');

  const loadMembers = useCallback(async () => {
    setLoading(true);
    if (!session) {
      setMembers([]);
      setLoading(false);
      return;
    }

    // Only show family members from THIS account's household
    const { data: hh } = await supabase
      .from('households')
      .select('id')
      .eq('owner_id', session.user.id)
      .limit(1);
    const householdId = hh && hh.length ? hh[0].id : null;

    if (!householdId) {
      setMembers([]);
      setLoading(false);
      return;
    }

    const { data, error } = await supabase
      .from('family_members')
      .select('id, display_name, member_photos(status)')
      .eq('household_id', householdId)
      .order('created_at', { ascending: false });
    if (!error && data) setMembers(data as FamilyMember[]);
    setLoading(false);
  }, [session]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  async function ensureHousehold(): Promise<string | null> {
    if (!session) return null;
    const uid = session.user.id;

    const { data: existing } = await supabase
      .from('households')
      .select('id')
      .eq('owner_id', uid)
      .limit(1);
    if (existing && existing.length > 0) return existing[0].id;

    const { data: created, error } = await supabase
      .from('households')
      .insert({ name: 'My Home', owner_id: uid })
      .select('id')
      .single();
    if (error || !created) {
      notify('Error', 'Could not create household: ' + (error?.message ?? ''));
      return null;
    }
    await supabase
      .from('household_members')
      .insert({ household_id: created.id, user_id: uid, role: 'owner' });
    return created.id;
  }

  async function addMember() {
    if (!name.trim()) {
      notify('Missing name', 'Please type the person’s name first.');
      return;
    }
    if (!session) {
      notify('Not signed in', 'Please sign in again.');
      return;
    }

    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      notify('Permission needed', 'Please allow photo access.');
      return;
    }

    const picked = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsMultipleSelection: true,
      selectionLimit: 5,
      quality: 0.7,
      base64: true,
    });
    if (picked.canceled || picked.assets.length === 0) return;

    setSaving(true);
    try {
      const householdId = await ensureHousehold();
      if (!householdId) return;

      const { data: member, error: memberErr } = await supabase
        .from('family_members')
        .insert({
          household_id: householdId,
          display_name: name.trim(),
          created_by: session.user.id,
        })
        .select('id')
        .single();
      if (memberErr || !member) {
        notify('Error', 'Could not save member: ' + (memberErr?.message ?? ''));
        return;
      }

      let uploaded = 0;
      for (let i = 0; i < picked.assets.length; i++) {
        const asset = picked.assets[i];
        if (!asset.base64) continue;

        const path = `${householdId}/${member.id}/${Date.now()}_${i}.jpg`;
        const bytes = base64ToBytes(asset.base64);

        const { error: upErr } = await supabase.storage
          .from('faces')
          .upload(path, bytes.buffer as ArrayBuffer, { contentType: 'image/jpeg' });
        if (upErr) continue;

        const { error: photoErr } = await supabase
          .from('member_photos')
          .insert({ member_id: member.id, storage_path: path });
        if (!photoErr) uploaded++;
      }

      if (uploaded === 0) {
        notify('Upload failed', 'No photos could be uploaded. Please try again.');
      } else {
        notify(
          'Added!',
          `${name.trim()} saved with ${uploaded} photo(s). The camera will learn this face within about a minute.`,
        );
        setName('');
      }
      await loadMembers();
    } finally {
      setSaving(false);
    }
  }

  function deleteMember(m: FamilyMember) {
    confirmDialog(
      `Remove "${m.display_name}"? The camera will stop recognizing them.`,
      async () => {
        const { error } = await supabase.from('family_members').delete().eq('id', m.id);
        if (error) notify('Delete failed', error.message);
        await loadMembers();
      },
    );
  }

  function statusLine(m: FamilyMember): string {
    const total = m.member_photos.length;
    const done = m.member_photos.filter((p) => p.status === 'processed').length;
    const rejected = m.member_photos.filter((p) => p.status === 'rejected').length;
    if (total === 0) return 'No photos';
    if (done === total) return `✅ Recognized (${done} photo${done > 1 ? 's' : ''})`;
    if (rejected === total) return '❌ Photos rejected — try clearer face photos';
    return `⏳ Learning… ${done}/${total} photos processed`;
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Family Faces</Text>
      <Text style={styles.subtitle}>
        People added here will be recognized by the SafeHaven camera.
      </Text>

      <View style={styles.addCard}>
        <Text style={styles.label}>Person&apos;s name</Text>
        <TextInput
          style={styles.input}
          value={name}
          onChangeText={setName}
          placeholder="e.g., Grandma, Uncle Ali"
          editable={!saving}
        />
        <View style={{ height: 12 }} />
        <Button
          title={saving ? 'Uploading…' : '\u{1F4F7} Choose photos & add'}
          onPress={addMember}
          disabled={saving}
        />
        <Text style={styles.hint}>
          Pick 1–5 clear photos of their face (one person per photo).
        </Text>
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 24 }} />
      ) : (
        members.map((m) => (
          <View key={m.id} style={styles.memberCard}>
            <View style={{ flex: 1 }}>
              <Text style={styles.memberName}>{m.display_name}</Text>
              <Text style={styles.memberStatus}>{statusLine(m)}</Text>
            </View>
            <Pressable onPress={() => deleteMember(m)} style={styles.deleteBtn}>
              <Ionicons name="trash-outline" size={20} color={Colors.danger} />
            </Pressable>
          </View>
        ))
      )}

      {!loading && members.length === 0 ? (
        <Text style={styles.empty}>No family members yet. Add the first one above!</Text>
      ) : null}

      <View style={{ height: 12 }} />
      <Button title="Refresh" variant="ghost" onPress={loadMembers} />
      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  content: { padding: 20 },
  title: { fontSize: 26, fontWeight: '800', color: Colors.text },
  subtitle: { marginTop: 6, marginBottom: 16, color: Colors.muted },
  addCard: {
    backgroundColor: Colors.card,
    borderColor: Colors.border,
    borderWidth: 1,
    borderRadius: 18,
    padding: 16,
    marginBottom: 18,
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
  hint: { marginTop: 10, color: Colors.muted, fontSize: 12 },
  memberCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.card,
    borderColor: Colors.border,
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
    marginBottom: 10,
  },
  memberName: { fontSize: 17, fontWeight: '700', color: Colors.text },
  memberStatus: { marginTop: 4, color: Colors.muted, fontSize: 13 },
  deleteBtn: { padding: 8, borderRadius: 10, backgroundColor: '#FFF0F0' },
  empty: { color: Colors.muted, textAlign: 'center', marginTop: 12 },
});
