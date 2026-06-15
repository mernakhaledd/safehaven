import { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Screen } from '../../../src/components/ui/Screen';
import { Card } from '../../../src/components/ui/Card';
import { Colors } from '../../../src/theme/colors';
import { supabase } from '../../../src/lib/supabase';
import { useProfile } from '../../../src/providers/ProfileProvider';
import { useAuth } from '../../../src/providers/AuthProvider';

export default function DoorLockScreen() {
  const { session } = useAuth();
  const { activeProfile, textSize, highContrast } = useProfile();
  const [isLocked, setIsLocked] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const [logs, setLogs] = useState<any[]>([]);
  const [logsLoading, setLogsLoading] = useState(true);

  // Security passcode verification states
  const [pinModalOpen, setPinModalOpen] = useState(false);
  const [pinCode, setPinCode] = useState('');
  const [targetDoorState, setTargetDoorState] = useState<boolean | null>(null);

  const fontScale = textSize === 'large' ? 1.25 : textSize === 'xl' ? 1.5 : 1.0;
  const dynamicText = (baseSize: number) => ({
    fontSize: baseSize * fontScale,
    ...(highContrast ? { color: '#000000', fontWeight: 'bold' as const } : {}),
  });
  const dynamicBg = (style: object) => [
    style,
    highContrast && { backgroundColor: '#ffffff', borderColor: '#000000', borderWidth: 2 },
  ];

  async function fetchLogs() {
    try {
      const { data, error } = await supabase
        .from('door_logs')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(10);
      if (!error && data) {
        setLogs(data);
      }
    } catch (err) {
      console.error('[Safe Haven] door logs fetch error:', err);
    } finally {
      setLogsLoading(false);
    }
  }

  async function fetchDoorStatus() {
    try {
      const { data, error } = await supabase
        .from('door_status')
        .select('is_locked, updated_at')
        .eq('id', 1)
        .single();

      if (error && error.code !== 'PGRST116') {
        console.error('[Safe Haven] door status fetch error:', error);
      }
      if (data) {
        setIsLocked(data.is_locked);
        setLastUpdated(data.updated_at);
      } else {
        await supabase.from('door_status').insert({ id: 1, is_locked: true });
        setIsLocked(true);
      }
    } catch (e) {
      console.error('[Safe Haven] door fetch threw:', e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchDoorStatus();
    fetchLogs();

    const ch = supabase
      .channel('door_status_changes')
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'door_status' },
        (payload) => {
          if (payload.new.id === 1) {
            setIsLocked(payload.new.is_locked);
            setLastUpdated(payload.new.updated_at);
          }
        }
      )
      .subscribe();

    const logsCh = supabase
      .channel('door_logs_changes')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'door_logs' },
        (payload) => {
          setLogs((prev) => [payload.new, ...prev].slice(0, 10));
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(ch);
      supabase.removeChannel(logsCh);
    };
  }, []);

  async function executeToggleDoor(targetState: boolean) {
    if (toggling) return;
    setToggling(true);
    const prev = isLocked;
    setIsLocked(targetState); // optimistic

    try {
      // 1. Audit Log Insertion
      await supabase.from('door_logs').insert({
        user_id: session?.user.id,
        profile_name: activeProfile?.displayName || 'Caregiver',
        action: targetState ? 'locked' : 'unlocked'
      });

      // 2. Door Status Update
      const { error } = await supabase
        .from('door_status')
        .update({ is_locked: targetState })
        .eq('id', 1);

      if (error) throw error;
    } catch (error) {
      Alert.alert('Error', 'Failed to update door status. Please try again.');
      setIsLocked(prev); // revert
    } finally {
      setToggling(false);
    }
  }

  async function toggleDoor(targetState: boolean) {
    // Only prompt PIN when unlocking (targetState === false)
    if (targetState === false) {
      const { secureStore } = await import('../../../src/lib/secureStore');
      const pinEnabled = await secureStore.getItem('pref_pin_enabled');
      if (pinEnabled === 'true') {
        setTargetDoorState(targetState);
        setPinCode('');
        setPinModalOpen(true);
        return;
      }
    }
    await executeToggleDoor(targetState);
  }

  function formatTime(iso: string | null) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) +
      ' · ' + d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }

  if (loading) {
    return (
      <Screen style={styles.loadingScreen}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Loading door status…</Text>
      </Screen>
    );
  }

  const locked = isLocked === true;

  return (
    <Screen style={highContrast ? { backgroundColor: '#ffffff' } : undefined}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={[styles.title, dynamicText(26)]}>Smart Door Lock</Text>
        <Text style={[styles.subtitle, dynamicText(13), highContrast && { color: '#333333' }]}>Real-time control and status</Text>

        {/* Big status circle */}
        <View style={styles.circleWrap}>
          <View style={[styles.circlePulse, { backgroundColor: locked ? '#FFECEC' : '#F0FFF4' }]} />
          <View style={[styles.circle, { backgroundColor: locked ? '#FFF5F5' : '#F0FFF4', borderColor: locked ? Colors.danger : Colors.success }, highContrast && { borderWidth: 3, borderColor: '#000000', backgroundColor: '#ffffff' }]}>
            <Ionicons
              name={locked ? 'lock-closed' : 'lock-open'}
              size={52}
              color={highContrast ? '#000000' : (locked ? Colors.danger : Colors.success)}
            />
            <Text style={[styles.circleLabel, dynamicText(16), { color: highContrast ? '#000000' : (locked ? Colors.danger : Colors.success) }]}>
              {locked ? 'LOCKED' : 'UNLOCKED'}
            </Text>
          </View>
        </View>

        {/* Last update info */}
        {lastUpdated && (
          <View style={styles.lastUpdateRow}>
            <Ionicons name="time-outline" size={14} color={highContrast ? '#000' : Colors.muted} />
            <Text style={[styles.lastUpdateText, dynamicText(13), highContrast && { color: '#000' }]}>Last changed {formatTime(lastUpdated)}</Text>
          </View>
        )}

        {/* Realtime indicator */}
        <View style={[styles.realtimeBadge, highContrast && { borderColor: '#000', backgroundColor: '#fff' }]}>
          <View style={[styles.realtimeDot, highContrast && { backgroundColor: '#000' }]} />
          <Text style={[styles.realtimeText, dynamicText(12), highContrast && { color: '#000' }]}>Synced with Raspberry Pi in real time</Text>
        </View>

        {/* Action buttons */}
        <View style={styles.buttonsRow}>
          <Pressable
            style={({ pressed }) => [
              styles.actionBtn,
              styles.lockBtn,
              locked && styles.actionBtnActive,
              (pressed || toggling) && { opacity: 0.85 },
              highContrast && { borderWidth: 2, borderColor: '#000' },
            ]}
            onPress={() => toggleDoor(true)}
            disabled={toggling || locked}
          >
            <Ionicons name="lock-closed" size={22} color="#fff" />
            <Text style={[styles.actionBtnText, dynamicText(17)]}>Lock</Text>
          </Pressable>

          <Pressable
            style={({ pressed }) => [
              styles.actionBtn,
              styles.unlockBtn,
              !locked && styles.actionBtnActive,
              (pressed || toggling) && { opacity: 0.85 },
              highContrast && { borderWidth: 2, borderColor: '#000' },
            ]}
            onPress={() => toggleDoor(false)}
            disabled={toggling || !locked}
          >
            {toggling
              ? <ActivityIndicator color="#fff" size="small" />
              : <Ionicons name="lock-open" size={22} color="#fff" />
            }
            <Text style={[styles.actionBtnText, dynamicText(17)]}>Unlock</Text>
          </Pressable>
        </View>

        {/* Info card */}
        <View style={dynamicBg(styles.infoCard)}>
          <Ionicons name="information-circle-outline" size={18} color={highContrast ? '#000' : Colors.primary} />
          <Text style={[styles.infoText, dynamicText(13), highContrast && { color: '#000' }]}>
            Changes here are instantly synced to the Raspberry Pi door controller via Supabase Realtime.
          </Text>
        </View>

        {/* Recent Activity Log section */}
        <Card style={dynamicBg(styles.logsCard)}>
          <Text style={[styles.logsTitle, dynamicText(16)]}>🔑 Recent Activity Log</Text>
          <View style={styles.logsDivider} />
          {logsLoading ? (
            <ActivityIndicator size="small" style={{ marginVertical: 12 }} />
          ) : logs.length === 0 ? (
            <Text style={[styles.logsEmpty, dynamicText(13)]}>No door actions recorded yet.</Text>
          ) : (
            <View style={{ gap: 10 }}>
              {logs.map((item) => (
                <View key={item.id.toString()} style={styles.logRow}>
                  <Ionicons
                    name={item.action === 'locked' ? 'lock-closed-outline' : 'lock-open-outline'}
                    size={18}
                    color={item.action === 'locked' ? Colors.danger : Colors.success}
                  />
                  <View style={{ flex: 1 }}>
                    <Text style={[styles.logText, dynamicText(13)]}>
                      Door <Text style={{ fontWeight: 'bold' }}>{item.action.toUpperCase()}</Text> by {item.profile_name}
                    </Text>
                    <Text style={styles.logTime}>{formatTime(item.created_at)}</Text>
                  </View>
                </View>
              ))}
            </View>
          )}
        </Card>
      </ScrollView>

      {/* Pin keypad modal */}
      <Modal visible={pinModalOpen} transparent animationType="slide" onRequestClose={() => setPinModalOpen(false)}>
        <View style={styles.pinModalOverlay}>
          <Card style={dynamicBg(styles.pinCard)}>
            <Text style={[styles.pinTitle, dynamicText(18)]}>Security Verification</Text>
            <Text style={[styles.pinSubtitle, dynamicText(13)]}>Enter 4-Digit PIN to unlock door</Text>
            <Text style={styles.pinDisplay}>{'*'.repeat(pinCode.length) || ' '}</Text>
            
            <View style={styles.keypad}>
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 'Clear', 0, 'Cancel'].map((key) => (
                <Pressable
                  key={key.toString()}
                  style={({ pressed }) => [styles.keypadBtn, pressed && { opacity: 0.7 }]}
                  onPress={async () => {
                    if (key === 'Cancel') {
                      setPinModalOpen(false);
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
                            setPinModalOpen(false);
                            if (targetDoorState !== null) {
                              executeToggleDoor(targetDoorState);
                            }
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
          </Card>
        </View>
      </Modal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  loadingScreen: { alignItems: 'center', justifyContent: 'center', gap: 12 },
  loadingText: { color: Colors.muted, fontWeight: '600' },

  content: { gap: 16, paddingBottom: 40, alignItems: 'center' },
  title: { fontSize: 26, fontWeight: '900', color: Colors.text, alignSelf: 'flex-start' },
  subtitle: { color: Colors.muted, fontSize: 13, alignSelf: 'flex-start', marginTop: 2 },

  circleWrap: { alignItems: 'center', justifyContent: 'center', marginTop: 16, marginBottom: 8 },
  circlePulse: {
    position: 'absolute',
    width: 220, height: 220, borderRadius: 110,
    opacity: 0.5,
  },
  circle: {
    width: 190, height: 190, borderRadius: 95,
    borderWidth: 3,
    alignItems: 'center', justifyContent: 'center', gap: 10,
    shadowColor: '#000', shadowOpacity: 0.08, shadowRadius: 20, shadowOffset: { width: 0, height: 6 },
  },
  circleLabel: { fontSize: 16, fontWeight: '900', letterSpacing: 1 },

  lastUpdateRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  lastUpdateText: { color: Colors.muted, fontSize: 13, fontWeight: '600' },

  realtimeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#F0FFF4',
    borderWidth: 1,
    borderColor: '#C8F0D4',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
  },
  realtimeDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: Colors.success },
  realtimeText: { color: '#056B2E', fontSize: 12, fontWeight: '700' },

  buttonsRow: { flexDirection: 'row', gap: 12, width: '100%', marginTop: 8 },
  actionBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    borderRadius: 18,
    gap: 8,
    opacity: 0.35,
  },
  actionBtnActive: {
    opacity: 1,
    shadowColor: '#000', shadowOpacity: 0.15, shadowRadius: 10, shadowOffset: { width: 0, height: 4 },
  },
  lockBtn: { backgroundColor: Colors.danger },
  unlockBtn: { backgroundColor: Colors.success },
  actionBtnText: { color: '#fff', fontSize: 17, fontWeight: '800' },

  infoCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    backgroundColor: '#F0F6FF',
    borderWidth: 1,
    borderColor: '#DDE8FF',
    borderRadius: 14,
    padding: 14,
    width: '100%',
  },
  infoText: { flex: 1, color: Colors.primary, fontSize: 13, lineHeight: 18, fontWeight: '600' },

  // Logs styles
  logsCard: {
    width: '100%',
    padding: 16,
    gap: 10,
    backgroundColor: '#fff',
  },
  logsTitle: {
    fontWeight: '900',
    color: Colors.text,
  },
  logsDivider: {
    height: 1,
    backgroundColor: '#F1F5F9',
  },
  logsEmpty: {
    color: Colors.muted,
    textAlign: 'center',
    paddingVertical: 10,
  },
  logRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F8FAFC',
    paddingBottom: 8,
  },
  logText: {
    color: Colors.text,
    lineHeight: 18,
  },
  logTime: {
    color: Colors.muted,
    fontSize: 11,
    marginTop: 2,
  },

  // Pin verification style
  pinModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  pinCard: {
    width: '100%',
    maxWidth: 320,
    padding: 24,
    alignItems: 'center',
    gap: 12,
  },
  pinTitle: {
    fontWeight: '900',
    color: Colors.text,
  },
  pinSubtitle: {
    color: Colors.muted,
    textAlign: 'center',
  },
  pinDisplay: {
    fontSize: 32,
    height: 40,
    fontWeight: '800',
    color: Colors.primary,
    letterSpacing: 8,
    marginVertical: 10,
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
