import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';

import { Screen } from '../../../src/components/ui/Screen';
import { Colors } from '../../../src/theme/colors';
import { useAuth } from '../../../src/providers/AuthProvider';
import { supabase } from '../../../src/lib/supabase';

type Camera = {
  id: string;
  name: string;
  local_ip: string | null;
  vendor: string | null;
  status: 'online' | 'offline' | 'unknown';
  updated_at: string;
};

function StatusDot({ status }: { status: Camera['status'] }) {
  const color = status === 'online' ? Colors.success : status === 'offline' ? Colors.danger : Colors.muted;
  return <View style={[styles.statusDot, { backgroundColor: color }]} />;
}

export default function CaregiverCameras() {
  const { session } = useAuth();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newIp, setNewIp] = useState('');
  const [newVendor, setNewVendor] = useState('');
  const [saving, setSaving] = useState(false);

  // PIN security states
  const [pinRequired, setPinRequired] = useState(false);
  const [pinVerified, setPinVerified] = useState(false);
  const [pinCode, setPinCode] = useState('');

  useEffect(() => {
    (async () => {
      const { secureStore } = await import('../../../src/lib/secureStore');
      const enabled = await secureStore.getItem('pref_pin_enabled');
      if (enabled === 'true') {
        setPinRequired(true);
      }
    })();
  }, []);

  const load = useCallback(async () => {
    if (!session) return;
    const { data, error } = await supabase
      .from('cameras')
      .select('id, name, local_ip, vendor, status, updated_at')
      .order('created_at', { ascending: true });
    if (!error && data) setCameras(data as Camera[]);
    setLoading(false);
  }, [session]);

  const loadRef = useRef(load);
  useEffect(() => { loadRef.current = load; }, [load]);

  useEffect(() => {
    loadRef.current();
    const ch = supabase
      .channel('cameras_realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'cameras' }, () => loadRef.current())
      .subscribe();
    return () => { supabase.removeChannel(ch); };
  }, []);

  async function handleAdd() {
    if (!newName.trim()) { Alert.alert('Name required', 'Give this camera a name.'); return; }
    if (!session) return;
    setSaving(true);
    const { error } = await supabase.from('cameras').insert({
      user_id: session.user.id,
      name: newName.trim(),
      local_ip: newIp.trim() || null,
      vendor: newVendor.trim() || null,
      status: 'unknown',
    });
    setSaving(true); // reset state loader
    setSaving(false);
    if (error) { Alert.alert('Error', error.message); return; }
    setNewName(''); setNewIp(''); setNewVendor('');
    setAddOpen(false);
  }

  async function handleDelete(id: string, name: string) {
    Alert.alert(`Remove "${name}"?`, 'This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Remove', style: 'destructive',
        onPress: async () => {
          await supabase.from('cameras').delete().eq('id', id);
        },
      },
    ]);
  }

  async function cycleStatus(cam: Camera) {
    const next: Camera['status'] = cam.status === 'unknown' ? 'online' : cam.status === 'online' ? 'offline' : 'unknown';
    await supabase.from('cameras').update({ status: next }).eq('id', cam.id);
  }

  if (pinRequired && !pinVerified) {
    return (
      <Screen style={styles.pinOverlay}>
        <View style={styles.pinCard}>
          <Ionicons name="lock-closed" size={48} color={Colors.primary} style={{ marginBottom: 8 }} />
          <Text style={styles.pinTitle}>Security Verification</Text>
          <Text style={styles.pinSubtitle}>Enter 4-Digit PIN to access camera feeds</Text>
          <Text style={styles.pinDisplay}>{'*'.repeat(pinCode.length) || ' '}</Text>
          
          <View style={styles.keypad}>
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 'Clear', 0, 'Back'].map((key) => (
              <Pressable
                key={key.toString()}
                style={({ pressed }) => [styles.keypadBtn, pressed && { opacity: 0.7 }]}
                onPress={async () => {
                  if (key === 'Back') {
                    router.back();
                  } else if (key === 'Clear') {
                    setPinCode('');
                  } else {
                    const next = pinCode + key;
                    if (next.length <= 4) {
                      setPinCode(next);
                      if (next.length === 4) {
                        const { secureStore } = await import('../../../src/lib/secureStore');
                        const savedPin = (await secureStore.getItem('pref_pin_code')) || '1234';
                        if (next === savedPin) {
                          setPinVerified(true);
                        } else {
                          Alert.alert('Incorrect PIN', 'Please try again.');
                          setPinCode('');
                        }
                      }
                    }
                  }
                }}
              >
                <Text style={styles.keypadBtnText}>{key}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Cameras</Text>
          <Text style={styles.subtitle}>Household camera registry</Text>
        </View>
        <Pressable
          onPress={() => setAddOpen(true)}
          style={({ pressed }) => [styles.addBtn, pressed && { opacity: 0.85 }]}
        >
          <Ionicons name="add" size={16} color="#fff" />
          <Text style={styles.addBtnText}>Add</Text>
        </Pressable>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : cameras.length === 0 ? (
        <View style={styles.center}>
          <View style={styles.emptyIcon}>
            <Ionicons name="videocam-outline" size={40} color={Colors.muted} />
          </View>
          <Text style={styles.emptyTitle}>No cameras registered</Text>
          <Text style={styles.emptyBody}>
            Add your household cameras to keep track of their status and IP addresses.
          </Text>
        </View>
      ) : (
        <FlatList
          data={cameras}
          keyExtractor={(c) => c.id}
          contentContainerStyle={{ gap: 10, paddingTop: 16, paddingBottom: 24 }}
          renderItem={({ item }) => (
            <View style={styles.cameraCard}>
              <View style={styles.cameraLeft}>
                <View style={styles.cameraIcon}>
                  <Ionicons name="videocam" size={20} color={Colors.primary} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.cameraName}>{item.name}</Text>
                  <Text style={styles.cameraMeta}>
                    {item.local_ip ?? 'No IP set'}{item.vendor ? ` · ${item.vendor}` : ''}
                  </Text>
                </View>
              </View>
              <View style={styles.cameraRight}>
                <Pressable
                  onPress={() => cycleStatus(item)}
                  style={({ pressed }) => [styles.statusPill, pressed && { opacity: 0.7 }]}
                >
                  <StatusDot status={item.status} />
                  <Text style={[
                    styles.statusText,
                    { color: item.status === 'online' ? Colors.success : item.status === 'offline' ? Colors.danger : Colors.muted }
                  ]}>
                    {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
                  </Text>
                </Pressable>
                <Pressable
                  onPress={() => handleDelete(item.id, item.name)}
                  style={({ pressed }) => [styles.deleteBtn, pressed && { opacity: 0.7 }]}
                >
                  <Ionicons name="trash-outline" size={16} color={Colors.danger} />
                </Pressable>
              </View>
            </View>
          )}
        />
      )}

      {/* Add camera modal */}
      <Modal visible={addOpen} animationType="slide" transparent onRequestClose={() => setAddOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setAddOpen(false)} />
        <View style={styles.sheet}>
          <Text style={styles.sheetTitle}>Register a camera</Text>

          <Text style={styles.fieldLabel}>Camera name *</Text>
          <TextInput
            style={styles.input}
            value={newName}
            onChangeText={setNewName}
            placeholder="e.g., Living Room"
            placeholderTextColor={Colors.muted}
          />

          <Text style={[styles.fieldLabel, { marginTop: 12 }]}>Local IP address</Text>
          <TextInput
            style={styles.input}
            value={newIp}
            onChangeText={setNewIp}
            placeholder="e.g., 192.168.1.100"
            placeholderTextColor={Colors.muted}
            keyboardType="numbers-and-punctuation"
          />

          <Text style={[styles.fieldLabel, { marginTop: 12 }]}>Brand / vendor</Text>
          <TextInput
            style={styles.input}
            value={newVendor}
            onChangeText={setNewVendor}
            placeholder="e.g., Hikvision, TP-Link"
            placeholderTextColor={Colors.muted}
          />

          <View style={styles.sheetActions}>
            <Pressable
              onPress={() => setAddOpen(false)}
              style={({ pressed }) => [styles.cancelBtn, pressed && { opacity: 0.7 }]}
            >
              <Text style={styles.cancelBtnText}>Cancel</Text>
            </Pressable>
            <Pressable
              onPress={handleAdd}
              disabled={saving}
              style={({ pressed }) => [styles.saveBtn, pressed && { opacity: 0.85 }]}
            >
              {saving
                ? <ActivityIndicator color="#fff" />
                : <Text style={styles.saveBtnText}>Add camera</Text>
              }
            </Pressable>
          </View>
        </View>
      </Modal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
  title: { fontSize: 26, fontWeight: '900', color: Colors.text },
  subtitle: { color: Colors.muted, fontSize: 13, marginTop: 2 },
  addBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: Colors.primary, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999,
  },
  addBtnText: { color: '#fff', fontWeight: '800', fontSize: 13 },

  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12, padding: 32 },
  emptyIcon: {
    width: 72, height: 72, borderRadius: 36,
    backgroundColor: '#F1F5F9', alignItems: 'center', justifyContent: 'center', marginBottom: 4,
  },
  emptyTitle: { fontWeight: '900', color: Colors.text, fontSize: 17 },
  emptyBody: { color: Colors.muted, textAlign: 'center', lineHeight: 20, fontSize: 14 },

  cameraCard: {
    backgroundColor: Colors.white, borderWidth: 1, borderColor: Colors.border,
    borderRadius: 16, padding: 14,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    shadowColor: '#000', shadowOpacity: 0.03, shadowRadius: 6, shadowOffset: { width: 0, height: 2 },
  },
  cameraLeft: { flexDirection: 'row', alignItems: 'center', gap: 12, flex: 1 },
  cameraIcon: {
    width: 42, height: 42, borderRadius: 12,
    backgroundColor: '#F0F6FF', alignItems: 'center', justifyContent: 'center',
  },
  cameraName: { fontWeight: '800', color: Colors.text, fontSize: 15 },
  cameraMeta: { color: Colors.muted, fontSize: 12, marginTop: 2 },
  cameraRight: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  statusDot: { width: 7, height: 7, borderRadius: 4 },
  statusPill: {
    flexDirection: 'row', alignItems: 'center', gap: 5,
    backgroundColor: '#F8FAFC', borderWidth: 1, borderColor: Colors.border,
    paddingHorizontal: 10, paddingVertical: 5, borderRadius: 10,
  },
  statusText: { fontSize: 12, fontWeight: '800' },
  deleteBtn: {
    width: 32, height: 32, borderRadius: 10,
    backgroundColor: '#FFF5F5', borderWidth: 1, borderColor: '#FFCDD2',
    alignItems: 'center', justifyContent: 'center',
  },

  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.35)' },
  sheet: {
    backgroundColor: Colors.white,
    borderTopLeftRadius: 24, borderTopRightRadius: 24,
    padding: 24, paddingBottom: 40,
  },
  sheetTitle: { fontSize: 20, fontWeight: '900', color: Colors.text, marginBottom: 16 },
  fieldLabel: { fontSize: 13, fontWeight: '700', color: Colors.text, marginBottom: 6 },
  input: {
    borderWidth: 1, borderColor: Colors.border,
    backgroundColor: '#F8FAFC', borderRadius: 12,
    paddingHorizontal: 14, paddingVertical: 12,
    fontSize: 16, color: Colors.text,
  },
  sheetActions: { flexDirection: 'row', gap: 10, marginTop: 20 },
  cancelBtn: {
    flex: 1, paddingVertical: 13, borderRadius: 14,
    borderWidth: 1, borderColor: Colors.border,
    alignItems: 'center',
  },
  cancelBtnText: { fontWeight: '800', color: Colors.text },
  saveBtn: {
    flex: 2, paddingVertical: 13, borderRadius: 14,
    backgroundColor: Colors.primary, alignItems: 'center',
    shadowColor: Colors.primary, shadowOpacity: 0.3, shadowRadius: 8, shadowOffset: { width: 0, height: 3 },
  },
  saveBtnText: { color: '#fff', fontWeight: '900', fontSize: 15 },

  // Pin verification overlay style
  pinOverlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 24,
  },
  pinCard: {
    width: '100%',
    maxWidth: 320,
    alignItems: 'center',
    gap: 12,
  },
  pinTitle: {
    fontSize: 22,
    fontWeight: '900',
    color: Colors.text,
  },
  pinSubtitle: {
    fontSize: 13,
    color: Colors.muted,
    textAlign: 'center',
  },
  pinDisplay: {
    fontSize: 32,
    height: 40,
    fontWeight: '800',
    color: Colors.primary,
    letterSpacing: 8,
    marginVertical: 12,
  },
  keypad: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 12,
    marginTop: 10,
  },
  keypadBtn: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: '#F1F5F9',
    justifyContent: 'center',
    alignItems: 'center',
  },
  keypadBtnText: {
    fontSize: 16,
    fontWeight: '800',
    color: Colors.text,
  },
});
