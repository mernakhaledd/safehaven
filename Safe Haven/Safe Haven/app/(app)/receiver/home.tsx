import { router } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Button } from '../../../src/components/ui/Button';
import { Card } from '../../../src/components/ui/Card';
import { Screen } from '../../../src/components/ui/Screen';
import { Colors } from '../../../src/theme/colors';
import { useAuth } from '../../../src/providers/AuthProvider';
import { useProfile } from '../../../src/providers/ProfileProvider';
import { supabase } from '../../../src/lib/supabase';
import { secureStore } from '../../../src/lib/secureStore';

type LinkedCaregiver = {
  link_id: string;
  caregiver_profile_id: string;
  caregiver_name: string;
};

type MedicineReminder = {
  id: string;
  medicineName: string;
  time: string; // Stored in "HH:MM" (24-hour format)
};

export default function ReceiverHome() {
  const { session } = useAuth();
  const { activeProfile, textSize, highContrast } = useProfile();
  const [caregivers, setCaregivers] = useState<LinkedCaregiver[]>([]);
  const [loading, setLoading] = useState(true);

  const [actionLoading, setActionLoading] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [activePing, setActivePing] = useState<{ id: string; senderName: string; fromProfileId: string; isScheduled?: boolean; reminderType?: 'medicine' | 'lunch'; medicineName?: string } | null>(null);
  const [promptedSchedules, setPromptedSchedules] = useState<Record<string, boolean>>({});

  // Medicine Reminders configurations
  const [remindersEnabled, setRemindersEnabled] = useState(true);
  const [reminders, setReminders] = useState<MedicineReminder[]>([]);
  const [addReminderOpen, setAddReminderOpen] = useState(false);
  const [newMedName, setNewMedName] = useState('');
  
  // iOS-style picker selections (12-hour formatting)
  const [selectedHour, setSelectedHour] = useState('08');
  const [selectedMinute, setSelectedMinute] = useState('00');
  const [selectedPeriod, setSelectedPeriod] = useState('AM');

  const caregiversRef = useRef(caregivers);
  useEffect(() => {
    caregiversRef.current = caregivers;
  }, [caregivers]);

  const loadRemindersConfig = useCallback(async () => {
    try {
      const enabled = await secureStore.getItem('pref_reminders_enabled');
      setRemindersEnabled(enabled !== 'false');

      const listStr = await secureStore.getItem('pref_medicine_reminders');
      if (listStr !== null) {
        setReminders(JSON.parse(listStr));
      } else {
        setReminders([]);
      }
    } catch (e) {
      console.error('[Safe Haven] failed to load reminders', e);
    }
  }, []);

  useEffect(() => {
    loadRemindersConfig();
  }, [loadRemindersConfig, addReminderOpen]);

  useEffect(() => {
    const t = setInterval(() => {
      loadRemindersConfig();
    }, 2000);
    return () => clearInterval(t);
  }, [loadRemindersConfig]);

  useEffect(() => {
    const checkSchedule = async () => {
      try {
        const enabled = await secureStore.getItem('pref_reminders_enabled');
        if (enabled === 'false') return;

        const listStr = await secureStore.getItem('pref_medicine_reminders');
        if (!listStr) return;
        const items: MedicineReminder[] = JSON.parse(listStr);

        const now = new Date();
        const hours = now.getHours();
        const minutes = now.getMinutes();
        const currentTimeStr = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
        const dateStr = now.toISOString().split('T')[0];

        for (const rem of items) {
          if (rem.time === currentTimeStr) {
            const key = `${dateStr}_${rem.id}`;
            if (!promptedSchedules[key]) {
              setPromptedSchedules((prev) => ({ ...prev, [key]: true }));
              setActivePing({
                id: 'sched_med_' + rem.id + '_' + Date.now(),
                senderName: 'Medicine Reminder',
                fromProfileId: 'system',
                isScheduled: true,
                reminderType: 'medicine',
                medicineName: rem.medicineName
              });
              const { playBeepSound } = await import('../../../src/lib/sound');
              playBeepSound();
            }
          }
        }
      } catch (err) {
        console.error('[Safe Haven Scheduler] error:', err);
      }
    };

    const intervalId = setInterval(checkSchedule, 15000); // Check every 15s
    return () => clearInterval(intervalId);
  }, [promptedSchedules]);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      if (session?.user?.id && activeProfile && activeProfile.persona === 'care_receiver') {
        const { data: people, error: peopleError } = await supabase
          .from('profiles')
          .select('id, display_name')
          .eq('user_id', session.user.id)
          .eq('persona', 'care_giver');

        if (peopleError) {
          console.error('[Safe Haven] profiles query error:', peopleError);
          setCaregivers([]);
          return;
        }

        const next: LinkedCaregiver[] = (people ?? []).map((p) => {
          return {
            link_id: p.id,
            caregiver_profile_id: p.id,
            caregiver_name: p.display_name,
          };
        });
        setCaregivers(next);
      } else {
        setCaregivers([]);
      }
    } catch (e) {
      console.error('[Safe Haven] unexpected error in receiver load:', e);
    } finally {
      if (!silent) setLoading(false);
    }
  }, [session, activeProfile]);

  const loadRef = useRef(load);
  useEffect(() => { loadRef.current = load; }, [load]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const channel = supabase
      .channel('receiver_inbox')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'profiles' }, () => loadRef.current(true))
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'nudges' }, async (payload) => {
        const nudge = payload.new;
        if (nudge && nudge.to_profile_id === activeProfile?.id && nudge.type === 'ping') {
          const { secureStore: ss } = await import('../../../src/lib/secureStore');
          const push = await ss.getItem('pref_push');
          const sound = await ss.getItem('pref_sound');

          if (push !== 'false') {
            let senderName = 'Caregiver';
            const cg = caregiversRef.current.find((c) => c.caregiver_profile_id === nudge.from_profile_id);
            if (cg) {
              senderName = cg.caregiver_name;
            } else {
              const { data: profile } = await supabase
                .from('profiles')
                .select('display_name')
                .eq('id', nudge.from_profile_id)
                .maybeSingle();
              if (profile?.display_name) {
                senderName = profile.display_name;
              }
            }
            setActivePing({
              id: nudge.id,
              senderName,
              fromProfileId: nudge.from_profile_id,
            });
          }

          if (sound !== 'false') {
            const { playBeepSound } = await import('../../../src/lib/sound');
            playBeepSound();
          }
        }
      })
      .subscribe();
    return () => { supabase.removeChannel(channel); };
  }, [activeProfile]);

  async function handleRequestHelp() {
    if (!activeProfile || !session) {
      setActionError('Session or profile not loaded.');
      return;
    }
    setActionLoading(true);
    setActionSuccess(null);
    setActionError(null);

    try {
      if (caregivers.length > 0) {
        const helpInserts = caregivers.map((c) => ({
          user_id: session.user.id,
          from_profile_id: activeProfile.id,
          to_profile_id: c.caregiver_profile_id,
          status: 'open',
        }));
        const { error: helpError } = await supabase.from('help_requests').insert(helpInserts);
        if (helpError) throw helpError;
      }

      const { error: alertError } = await supabase.from('alerts').insert({
        type: 'IMMEDIATE_HELP_REQUEST',
        person_name: activeProfile.displayName,
        confidence: 1.0,
        status: 'new',
        user_id: session.user.id,
      });
      if (alertError) throw alertError;

      if (caregivers.length > 0) {
        setActionSuccess('🚨 Emergency Help Request sent to all caregivers!');
      } else {
        setActionSuccess('🚨 Emergency Help Request registered in cloud alerts!');
      }
    } catch (err) {
      console.error('[Safe Haven] help request failed', err);
      setActionError('Failed to send emergency request.');
    } finally {
      setActionLoading(false);
    }
  }

  async function handlePingCaregivers() {
    if (!activeProfile || caregivers.length === 0 || !session) {
      setActionError('No caregivers in this account to ping.');
      return;
    }
    setActionLoading(true);
    setActionSuccess(null);
    setActionError(null);

    try {
      const nudgeInserts = caregivers.map((c) => ({
        user_id: session.user.id,
        from_profile_id: activeProfile.id,
        to_profile_id: c.caregiver_profile_id,
        type: 'ping',
      }));

      const { error: nudgeError } = await supabase.from('nudges').insert(nudgeInserts);
      if (nudgeError) throw nudgeError;

      setActionSuccess('🔔 Pinged caregivers successfully!');
    } catch (err) {
      console.error('[Safe Haven] ping failed', err);
      setActionError('Failed to ping caregivers.');
    } finally {
      setActionLoading(false);
    }
  }

  async function handleAcknowledgePing() {
    if (!activePing || !activeProfile || !session) return;
    const senderId = activePing.fromProfileId;
    setActivePing(null);

    try {
      if (senderId === 'system' && caregiversRef.current.length > 0) {
        const nudgeInserts = caregiversRef.current.map((c) => ({
          user_id: session.user.id,
          from_profile_id: activeProfile.id,
          to_profile_id: c.caregiver_profile_id,
          type: 'check_in',
        }));
        const { error } = await supabase.from('nudges').insert(nudgeInserts);
        if (error) throw error;
      } else {
        const { error } = await supabase.from('nudges').insert({
          user_id: session.user.id,
          from_profile_id: activeProfile.id,
          to_profile_id: senderId === 'system' ? activeProfile.id : senderId,
          type: 'check_in',
        });
        if (error) throw error;
      }
      setActionSuccess("Sent 'I'm OK' response to caregiver!");
    } catch (err) {
      console.error('[Safe Haven] failed to send check-in response', err);
      setActionError('Failed to send check-in response.');
    }
  }

  async function handleChatWithCaregiver(caregiverProfileId: string) {
    if (!activeProfile || !session) return;
    try {
      const { data: conversationId, error } = await supabase.rpc('get_or_create_conversation', {
        p_giver_profile_id: caregiverProfileId,
        p_receiver_profile_id: activeProfile.id,
      });
      if (error) throw error;
      router.push({ pathname: '/(app)/receiver/chats', params: { autoOpen: conversationId } });
    } catch (err) {
      console.error('[Safe Haven] caregiver chat routing failed', err);
      Alert.alert('Error', 'Failed to open chat.');
    }
  }

  async function handleAddReminder() {
    if (!newMedName.trim()) {
      Alert.alert('Required', 'Please enter a medicine name.');
      return;
    }
    
    // Convert 12-hour AM/PM selection to 24-hour HH:MM format for scheduler
    let h = parseInt(selectedHour);
    if (selectedPeriod === 'PM' && h < 12) {
      h += 12;
    } else if (selectedPeriod === 'AM' && h === 12) {
      h = 0;
    }
    const time24 = `${h.toString().padStart(2, '0')}:${selectedMinute}`;

    const newRem: MedicineReminder = {
      id: Date.now().toString(),
      medicineName: newMedName.trim(),
      time: time24,
    };
    const nextList = [...reminders, newRem].sort((a, b) => a.time.localeCompare(b.time));
    setReminders(nextList);
    await secureStore.setItem('pref_medicine_reminders', JSON.stringify(nextList));
    setNewMedName('');
    setAddReminderOpen(false);
  }

  async function handleDeleteReminder(id: string) {
    const nextList = reminders.filter((r) => r.id !== id);
    setReminders(nextList);
    await secureStore.setItem('pref_medicine_reminders', JSON.stringify(nextList));
  }

  // Format 24-hour time to 12-hour AM/PM string for display
  function formatTime12(time24: string) {
    const [hStr, mStr] = time24.split(':');
    let h = parseInt(hStr);
    const period = h >= 12 ? 'PM' : 'AM';
    let h12 = h % 12;
    if (h12 === 0) h12 = 12;
    return `${h12.toString().padStart(2, '0')}:${mStr} ${period}`;
  }

  const fontScale = textSize === 'large' ? 1.25 : textSize === 'xl' ? 1.5 : 1.0;
  const dynamicText = (baseSize: number) => ({
    fontSize: baseSize * fontScale,
    ...(highContrast ? { color: '#000000', fontWeight: 'bold' as const } : {}),
  });
  const dynamicBg = (style: object) => [
    style,
    highContrast && { backgroundColor: '#ffffff', borderColor: '#000000', borderWidth: 2 },
  ];

  return (
    <Screen style={highContrast ? { backgroundColor: '#ffffff' } : undefined}>
      <ScrollView contentContainerStyle={{ gap: 12, paddingBottom: 24 }}>
        <Text style={[styles.title, dynamicText(26)]}>Care Receiver</Text>
        <Text style={[styles.subtitle, dynamicText(14), highContrast && { color: '#333333' }]}>
          {activeProfile ? `Hi, ${activeProfile.displayName}` : 'Your home screen adapts to who you are.'}
        </Text>

        <Card style={dynamicBg(styles.card)}>
          <Text style={[styles.cardTitle, dynamicText(16)]}>Need help?</Text>
          <Text style={[styles.cardBody, dynamicText(14), highContrast && { color: '#333333' }]}>
            Use these buttons to instantly alert or notify your linked caregivers.
          </Text>

          {actionSuccess ? (
            <View style={styles.successBox}>
              <Text style={styles.successText}>{actionSuccess}</Text>
            </View>
          ) : null}

          {actionError ? (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{actionError}</Text>
            </View>
          ) : null}

          {caregivers.length === 0 ? (
            <Text style={[styles.empty, dynamicText(13), { color: '#E28743', marginTop: 10 }]}>
              ⚠️ No caregivers created in this account yet. Please create one in profiles to link dashboards.
            </Text>
          ) : null}

          <View style={{ height: 12 }} />
          <Button
            title={actionLoading ? 'Sending Alert...' : 'Request immediate help'}
            variant="danger"
            disabled={actionLoading}
            onPress={handleRequestHelp}
            style={highContrast ? { borderWidth: 2, borderColor: '#000' } : undefined}
          />
          <View style={{ height: 10 }} />
          <Button
            title={actionLoading ? 'Pinging...' : 'Ping caregiver'}
            variant="secondary"
            disabled={actionLoading || caregivers.length === 0}
            onPress={handlePingCaregivers}
            style={highContrast ? { borderWidth: 2, borderColor: '#000' } : undefined}
          />
        </Card>

        {/* Dashboard Medicine Reminders Section */}
        {remindersEnabled && (
          <Card style={dynamicBg(styles.card)}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text style={[styles.cardTitle, dynamicText(16)]}>Medicine Reminders</Text>
              <Pressable
                style={({ pressed }) => [styles.addBtn, pressed && { opacity: 0.8 }]}
                onPress={() => setAddReminderOpen(true)}
              >
                <Ionicons name="add" size={14} color="#fff" />
                <Text style={styles.addBtnText}>Add</Text>
              </Pressable>
            </View>
            <View style={styles.divider} />

            {reminders.length === 0 ? (
              <Text style={[styles.empty, dynamicText(13), { textAlign: 'center', paddingVertical: 12 }]}>
                No medication alarms scheduled.
              </Text>
            ) : (
              <View style={{ gap: 10 }}>
                {reminders.map((r) => (
                  <View key={r.id} style={styles.reminderRow}>
                    <Ionicons name="alarm-outline" size={20} color={Colors.primary} />
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.reminderName, dynamicText(14)]}>{r.medicineName}</Text>
                      <Text style={[styles.reminderTime, dynamicText(12)]}>Daily at {formatTime12(r.time)}</Text>
                    </View>
                    <Pressable
                      style={({ pressed }) => [styles.deleteBtn, pressed && { opacity: 0.75 }]}
                      onPress={() => handleDeleteReminder(r.id)}
                    >
                      <Ionicons name="trash-outline" size={16} color={Colors.danger} />
                    </Pressable>
                  </View>
                ))}
              </View>
            )}
          </Card>
        )}

        <Card style={dynamicBg(styles.card)}>
          <Text style={[styles.cardTitle, dynamicText(16)]}>My caregivers</Text>
          {loading ? (
            <ActivityIndicator style={{ marginTop: 12 }} />
          ) : caregivers.length === 0 ? (
            <Text style={[styles.empty, dynamicText(14), highContrast && { color: '#333333' }]}>
              No caregivers found in this family account. Please create one in profiles.
            </Text>
          ) : (
            <View style={{ gap: 8, marginTop: 8 }}>
              {caregivers.map((c) => (
                <View key={c.link_id} style={styles.caregiverRow}>
                  <View style={styles.avatar}>
                    <Text style={styles.avatarText}>
                      {c.caregiver_name.charAt(0).toUpperCase()}
                    </Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={[styles.caregiverName, dynamicText(14)]}>{c.caregiver_name}</Text>
                    <Text style={[styles.caregiverMeta, dynamicText(12), highContrast && { color: '#444' }]}>
                      Care giver
                    </Text>
                  </View>
                  <Pressable
                    style={({ pressed }) => [
                      styles.chatCircleBtn,
                      pressed && { opacity: 0.75 },
                      highContrast && { borderWidth: 1, borderColor: '#000000' }
                    ]}
                    onPress={() => handleChatWithCaregiver(c.caregiver_profile_id)}
                  >
                    <Ionicons name="chatbubble-ellipses" size={16} color="#fff" />
                  </Pressable>
                  <View style={styles.dot} />
                </View>
              ))}
            </View>
          )}
        </Card>
      </ScrollView>

      <Modal
        visible={activePing !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setActivePing(null)}
      >
        <View style={styles.modalOverlay}>
          <Card style={dynamicBg(styles.modalCard)}>
            <View style={styles.modalHeader}>
              <Ionicons name="hand-right-outline" size={32} color={Colors.primary} />
              <Text style={[styles.modalTitle, dynamicText(20)]}>Are you OK?</Text>
            </View>
            <Text style={[styles.modalBody, dynamicText(14), highContrast && { color: '#333333' }]}>
              {activePing?.reminderType === 'medicine'
                ? `Time for your Medicine: ${activePing.medicineName || 'Medication'}! Please check in and take it.`
                : activePing ? `${activePing.senderName} is checking in on you.` : 'A caregiver is checking in.'}
            </Text>
            <View style={{ height: 16 }} />
            <Button
              title="Yes, I'm OK! 🟢"
              onPress={handleAcknowledgePing}
              style={highContrast ? { borderWidth: 2, borderColor: '#000' } : undefined}
            />
            <View style={{ height: 10 }} />
            <Button
              title="Dismiss"
              variant="ghost"
              onPress={() => setActivePing(null)}
            />
          </Card>
        </View>
      </Modal>

      {/* Add Reminder iOS-style Modal */}
      <Modal visible={addReminderOpen} transparent animationType="slide" onRequestClose={() => setAddReminderOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setAddReminderOpen(false)} />
        <View style={styles.sheet}>
          <Text style={styles.sheetTitle}>Add Medicine Reminder</Text>

          <Text style={styles.fieldLabel}>Medicine Name *</Text>
          <TextInput
            style={styles.input}
            value={newMedName}
            onChangeText={setNewMedName}
            placeholder="e.g. Aspirin, Panadol"
            placeholderTextColor={Colors.muted}
          />

          <Text style={[styles.fieldLabel, { marginTop: 14 }]}>Set Alarm Time (Select Hour, Minute & Period)</Text>
          
          <View style={styles.timePickerContainer}>
            {/* Hour Picker Column */}
            <View style={styles.pickerColumn}>
              <Text style={styles.pickerColumnLabel}>Hour</Text>
              <ScrollView style={styles.pickerScrollView} nestedScrollEnabled showsVerticalScrollIndicator={false}>
                {Array.from({ length: 12 }).map((_, i) => {
                  const hVal = (i + 1).toString().padStart(2, '0');
                  const isSelected = selectedHour === hVal;
                  return (
                    <Pressable
                      key={hVal}
                      style={[styles.pickerItem, isSelected && styles.pickerItemActive]}
                      onPress={() => setSelectedHour(hVal)}
                    >
                      <Text style={[styles.pickerItemText, isSelected && styles.pickerItemTextActive]}>{hVal}</Text>
                    </Pressable>
                  );
                })}
              </ScrollView>
            </View>

            {/* Minute Picker Column */}
            <View style={styles.pickerColumn}>
              <Text style={styles.pickerColumnLabel}>Minute</Text>
              <ScrollView style={styles.pickerScrollView} nestedScrollEnabled showsVerticalScrollIndicator={false}>
                {Array.from({ length: 60 }).map((_, i) => {
                  const mStr = i.toString().padStart(2, '0');
                  const isSelected = selectedMinute === mStr;
                  return (
                    <Pressable
                      key={mStr}
                      style={[styles.pickerItem, isSelected && styles.pickerItemActive]}
                      onPress={() => setSelectedMinute(mStr)}
                    >
                      <Text style={[styles.pickerItemText, isSelected && styles.pickerItemTextActive]}>{mStr}</Text>
                    </Pressable>
                  );
                })}
              </ScrollView>
            </View>

            {/* AM/PM Selector Column */}
            <View style={styles.pickerColumnSmall}>
              <Text style={styles.pickerColumnLabel}>Period</Text>
              <ScrollView style={styles.pickerScrollView} nestedScrollEnabled showsVerticalScrollIndicator={false}>
                {['AM', 'PM'].map((period) => {
                  const isSelected = selectedPeriod === period;
                  return (
                    <Pressable
                      key={period}
                      style={[styles.pickerItem, isSelected && styles.pickerItemActive]}
                      onPress={() => setSelectedPeriod(period)}
                    >
                      <Text style={[styles.pickerItemText, isSelected && styles.pickerItemTextActive]}>{period}</Text>
                    </Pressable>
                  );
                })}
              </ScrollView>
            </View>
          </View>

          <View style={styles.sheetActions}>
            <Pressable
              onPress={() => setAddReminderOpen(false)}
              style={({ pressed }) => [styles.cancelBtn, pressed && { opacity: 0.7 }]}
            >
              <Text style={styles.cancelBtnText}>Cancel</Text>
            </Pressable>
            <Pressable
              onPress={handleAddReminder}
              style={({ pressed }) => [styles.saveBtn, pressed && { opacity: 0.85 }]}
            >
              <Text style={styles.saveBtnText}>Save Alarm</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 26, fontWeight: '900', color: Colors.text },
  subtitle: { marginTop: 4, color: Colors.muted },
  card: {
    gap: 8,
    borderRadius: 24,
    padding: 20,
    backgroundColor: Colors.white,
    shadowColor: '#0F172A',
    shadowOpacity: 0.05,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
    borderWidth: 1,
    borderColor: '#F1F5F9',
  },
  cardTitle: { fontWeight: '900', color: Colors.text, fontSize: 17, letterSpacing: -0.2 },
  cardBody: { color: Colors.muted, lineHeight: 22, fontSize: 14 },
  empty: { color: Colors.muted, marginTop: 10, lineHeight: 20 },
  divider: { height: 1, backgroundColor: '#F8FAFC', marginVertical: 6 },
  
  caregiverRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F8FAFC',
  },
  chatCircleBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: Colors.primary,
    shadowOpacity: 0.25,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#F0FDF4',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#DCFCE7',
  },
  avatarText: { color: '#16A34A', fontWeight: '900', fontSize: 18 },
  caregiverName: { color: Colors.text, fontWeight: '800', fontSize: 15 },
  caregiverMeta: { color: Colors.muted, fontSize: 12, marginTop: 1 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: Colors.success },
  errorBox: {
    marginTop: 8,
    backgroundColor: '#FFE9E7',
    borderColor: '#FF3B30',
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
  },
  errorText: { color: '#8A1F19', fontWeight: '700' },
  successBox: {
    marginTop: 8,
    backgroundColor: '#E5F8EC',
    borderColor: '#34C759',
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
  },
  successText: { color: '#0F5C2E', fontWeight: '700' },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.3)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  modalCard: {
    width: '100%',
    maxWidth: 340,
    padding: 24,
    alignItems: 'center',
    gap: 8,
    borderRadius: 28,
  },
  modalHeader: {
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  modalTitle: {
    fontWeight: '900',
    color: Colors.text,
    textAlign: 'center',
  },
  modalBody: {
    color: Colors.muted,
    textAlign: 'center',
    lineHeight: 20,
  },

  // Custom reminders styles
  addBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: Colors.primary,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 99,
  },
  addBtnText: {
    color: '#fff',
    fontWeight: '800',
    fontSize: 12,
  },
  reminderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F8FAFC',
  },
  reminderName: {
    fontWeight: '800',
    color: Colors.text,
    fontSize: 15,
  },
  reminderTime: {
    color: Colors.muted,
    marginTop: 2,
    fontSize: 13,
  },
  deleteBtn: {
    width: 34,
    height: 34,
    borderRadius: 10,
    backgroundColor: '#FFF5F5',
    borderWidth: 1,
    borderColor: '#FFCDD2',
    justifyContent: 'center',
    alignItems: 'center',
  },
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.4)',
  },
  sheet: {
    backgroundColor: Colors.white,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 24,
    paddingBottom: 40,
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: -10 },
  },
  sheetTitle: {
    fontSize: 20,
    fontWeight: '900',
    color: Colors.text,
    marginBottom: 16,
    letterSpacing: -0.3,
  },
  fieldLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: Colors.text,
    marginBottom: 6,
  },
  input: {
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: '#F8FAFC',
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    color: Colors.text,
  },
  sheetActions: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 24,
  },
  cancelBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: 'center',
  },
  cancelBtnText: {
    fontWeight: '800',
    color: Colors.text,
  },
  saveBtn: {
    flex: 2,
    paddingVertical: 14,
    borderRadius: 16,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    shadowColor: Colors.primary,
    shadowOpacity: 0.25,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
  },
  saveBtnText: {
    color: '#fff',
    fontWeight: '900',
    fontSize: 15,
  },

  // iOS time spinner select layout
  timePickerContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    height: 150,
    backgroundColor: '#F8FAFC',
    borderRadius: 16,
    padding: 10,
    marginTop: 8,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  pickerColumn: {
    flex: 1.2,
    alignItems: 'center',
  },
  pickerColumnSmall: {
    flex: 0.8,
    alignItems: 'center',
  },
  pickerColumnLabel: {
    fontSize: 12,
    fontWeight: '800',
    color: Colors.muted,
    marginBottom: 6,
  },
  pickerScrollView: {
    width: '100%',
  },
  pickerItem: {
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 8,
    marginVertical: 1,
  },
  pickerItemActive: {
    backgroundColor: Colors.primary,
  },
  pickerItemText: {
    fontSize: 16,
    fontWeight: '600',
    color: Colors.text,
  },
  pickerItemTextActive: {
    color: '#fff',
    fontWeight: '900',
  },
});
