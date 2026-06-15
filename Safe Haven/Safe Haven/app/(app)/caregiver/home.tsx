import { router } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { EmergencyCall911 } from '../../../src/components/EmergencyCall911';
import { Button } from '../../../src/components/ui/Button';
import { Card } from '../../../src/components/ui/Card';
import { Screen } from '../../../src/components/ui/Screen';
import { Colors } from '../../../src/theme/colors';
import { useProfile } from '../../../src/providers/ProfileProvider';
import { useAuth } from '../../../src/providers/AuthProvider';
import { supabase } from '../../../src/lib/supabase';

type LinkedReceiver = {
  link_id: string;
  receiver_profile_id: string;
  receiver_name: string;
  receiver_type: string | null;
  has_active_help: boolean;
  help_request_id?: string;
};

export default function CaregiverHome() {
  const { session } = useAuth();
  const { activeProfile, textSize, highContrast } = useProfile();
  const [receivers, setReceivers] = useState<LinkedReceiver[]>([]);
  const [loading, setLoading] = useState(true);

  const [nudgeNotification, setNudgeNotification] = useState<{ id: string; message: string; type: 'ping' | 'check_in' } | null>(null);
  const [criticalAlert, setCriticalAlert] = useState<{ id: string; type: string; person_name?: string | null; confidence: number } | null>(null);

  const receiversRef = useRef(receivers);
  useEffect(() => {
    receiversRef.current = receivers;
  }, [receivers]);

  const fontScale = textSize === 'large' ? 1.25 : textSize === 'xl' ? 1.5 : 1.0;
  const dynamicText = (baseSize: number) => ({
    fontSize: baseSize * fontScale,
    ...(highContrast ? { color: '#000000', fontWeight: 'bold' as const } : {}),
  });
  const dynamicBg = (style: object) => [
    style,
    highContrast && { backgroundColor: '#ffffff', borderColor: '#000000', borderWidth: 2 },
  ];

  useEffect(() => {
    if (!nudgeNotification) return;
    const t = setTimeout(() => {
      setNudgeNotification(null);
    }, 6000);
    return () => clearTimeout(t);
  }, [nudgeNotification]);

  const load = useCallback(async (silent = false) => {
    if (!activeProfile || activeProfile.persona !== 'care_giver') {
      setReceivers([]);
      setLoading(false);
      return;
    }
    if (!silent) setLoading(true);

    try {
      // Netflix family logic: get all receiver profiles belonging to the same user account
      const { data: people, error: peopleError } = await supabase
        .from('profiles')
        .select('id, display_name, receiver_type')
        .eq('user_id', session?.user.id)
        .eq('persona', 'care_receiver');

      if (peopleError) {
        console.error('[Safe Haven] profiles query error:', peopleError);
        setReceivers([]);
        return;
      }

      const { data: activeHelpRequests, error: helpError } = await supabase
        .from('help_requests')
        .select('id, from_profile_id')
        .eq('to_profile_id', activeProfile.id)
        .eq('status', 'open');

      if (helpError) console.error('[Safe Haven] help_requests query error:', helpError);

      const next: LinkedReceiver[] = (people ?? []).map((p) => {
        const helpReq = (activeHelpRequests ?? []).find((h) => h.from_profile_id === p.id);
        return {
          link_id: p.id, // Use profile ID as key/link_id
          receiver_profile_id: p.id,
          receiver_name: p.display_name,
          receiver_type: p.receiver_type ?? null,
          has_active_help: !!helpReq,
          help_request_id: helpReq?.id,
        };
      });
      setReceivers(next);
    } catch (e) {
      console.error('[Safe Haven] unexpected error in caregiver load:', e);
    } finally {
      if (!silent) setLoading(false);
    }
  }, [activeProfile, session]);

  async function handlePingReceiver(receiverProfileId: string) {
    if (!activeProfile || !session) return;
    try {
      const { error } = await supabase.from('nudges').insert({
        user_id: session.user.id,
        from_profile_id: activeProfile.id,
        to_profile_id: receiverProfileId,
        type: 'ping',
      });
      if (error) throw error;
      Alert.alert('Success', 'Ping sent to care receiver!');
    } catch (err) {
      console.error('[Safe Haven] ping failed', err);
      Alert.alert('Error', 'Failed to send ping.');
    }
  }

  async function handleAcknowledgeHelp(helpRequestId: string) {
    try {
      const { error } = await supabase
        .from('help_requests')
        .update({ status: 'acknowledged' })
        .eq('id', helpRequestId);
      if (error) throw error;
      Alert.alert('Success', 'Emergency alert acknowledged.');
      load();
    } catch (err) {
      console.error('[Safe Haven] acknowledge failed', err);
      Alert.alert('Error', 'Failed to acknowledge alert.');
    }
  }

  async function handleChatWithReceiver(receiverProfileId: string) {
    if (!activeProfile) return;
    try {
      const { data: conversationId, error } = await supabase.rpc('get_or_create_conversation', {
        p_giver_profile_id: activeProfile.id,
        p_receiver_profile_id: receiverProfileId,
      });
      if (error) throw error;
      router.push({ pathname: '/(app)/caregiver/chats', params: { autoOpen: conversationId } });
    } catch (err) {
      console.error('[Safe Haven] chat routing failed', err);
      Alert.alert('Error', 'Failed to open chat.');
    }
  }

  const loadRef = useRef(load);
  useEffect(() => { loadRef.current = load; }, [load]);

  useEffect(() => {
    load();
  }, [activeProfile?.id]);

  useEffect(() => {
    const channel = supabase
      .channel('caregiver_dashboard_realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'profiles' }, () => loadRef.current(true))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'help_requests' }, () => loadRef.current(true))
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'alerts' }, async (payload) => {
        const alertVal = payload.new;
        if (alertVal) {
          const typeLower = alertVal.type.toLowerCase();
          if (typeLower.includes('fall') || typeLower.includes('help') || typeLower.includes('gesture')) {
            if (alertVal.user_id === session?.user.id) {
            const { secureStore } = await import('../../../src/lib/secureStore');
            const push = await secureStore.getItem('pref_push');
            const sound = await secureStore.getItem('pref_sound');

            if (push !== 'false') {
              setCriticalAlert({
                id: alertVal.id,
                type: alertVal.type,
                person_name: alertVal.person_name,
                confidence: alertVal.confidence,
              });
            }

            if (sound !== 'false') {
              const { playBeepSound } = await import('../../../src/lib/sound');
              playBeepSound();
              setTimeout(() => playBeepSound(), 200);
            }
            }
          }
        }
      })
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'help_requests' }, async (payload) => {
        const req = payload.new;
        if (req && req.to_profile_id === activeProfile?.id && req.status === 'open') {
          loadRef.current(true);

          const { secureStore } = await import('../../../src/lib/secureStore');
          const push = await secureStore.getItem('pref_push');
          const sound = await secureStore.getItem('pref_sound');

          if (push !== 'false') {
            const { data: p } = await supabase
              .from('profiles')
              .select('display_name')
              .eq('id', req.from_profile_id)
              .maybeSingle();
            const senderName = p?.display_name ?? 'Care Receiver';
            setNudgeNotification({
              id: req.id,
              message: `🚨 ALERT: ${senderName} requested immediate help!`,
              type: 'ping',
            });
          }

          if (sound !== 'false') {
            const { playBeepSound } = await import('../../../src/lib/sound');
            playBeepSound();
            setTimeout(() => playBeepSound(), 250);
          }
        }
      })
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'nudges' }, async (payload) => {
        const nudge = payload.new;
        if (nudge && nudge.to_profile_id === activeProfile?.id) {
          loadRef.current(true);

          const { secureStore } = await import('../../../src/lib/secureStore');
          const push = await secureStore.getItem('pref_push');
          const sound = await secureStore.getItem('pref_sound');

          if (push !== 'false') {
            let senderName = 'Care Receiver';
            const r = receiversRef.current.find((rec) => rec.receiver_profile_id === nudge.from_profile_id);
            if (r) {
              senderName = r.receiver_name;
            } else {
              const { data: p } = await supabase
                .from('profiles')
                .select('display_name')
                .eq('id', nudge.from_profile_id)
                .maybeSingle();
              if (p?.display_name) {
                senderName = p.display_name;
              }
            }

            const message = nudge.type === 'ping'
              ? `🔔 ${senderName} sent you a ping!`
              : `🟢 ${senderName} checked in: "I'm OK!"`;

            setNudgeNotification({
              id: nudge.id,
              message,
              type: nudge.type,
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
  }, [activeProfile, session]);

  return (
    <Screen style={highContrast ? { backgroundColor: '#ffffff' } : undefined}>
      {criticalAlert && (
        <Pressable
          style={[
            styles.criticalAlertBlock,
            highContrast && { borderWidth: 3, borderColor: '#000000', backgroundColor: '#ffffff' }
          ]}
          onPress={() => setCriticalAlert(null)}
        >
          <View style={{ flex: 1, gap: 4 }}>
            <Text style={[styles.criticalAlertHeader, highContrast && { color: '#000' }]}>🚨 CRITICAL EMERGENCY ALERT 🚨</Text>
            <Text style={[styles.criticalAlertBody, highContrast && { color: '#000' }]}>
              {criticalAlert.type.includes('FALL') 
                ? `🚨 Fall Detected – Immediate Attention May Be Required`
                : criticalAlert.type.includes('HELP') 
                  ? `⚠️ Emergency Help Gesture Detected – Immediate Attention Required`
                  : `${criticalAlert.type.replace(/_/g, ' ')} detected!`
              }
            </Text>
            <Text style={[styles.criticalAlertConfidence, highContrast && { color: '#000' }]}>
              Confidence level: {(criticalAlert.confidence * 100).toFixed(0)}%
            </Text>
          </View>
          <Ionicons name="close-circle" size={26} color={highContrast ? '#000000' : '#ffffff'} />
        </Pressable>
      )}
      {nudgeNotification && (
        <Pressable
          style={[
            styles.nudgeBanner,
            nudgeNotification.type === 'check_in' && styles.nudgeBannerSuccess,
          ]}
          onPress={() => setNudgeNotification(null)}
        >
          <Text style={styles.nudgeBannerText}>{nudgeNotification.message}</Text>
          <Ionicons name="close-circle-outline" size={18} color="#fff" />
        </Pressable>
      )}
      <ScrollView contentContainerStyle={{ gap: 12, paddingBottom: 80 }}>
        <Text style={[styles.title, dynamicText(26)]}>Care Giver</Text>
        <Text style={[styles.subtitle, dynamicText(14), highContrast && { color: '#333333' }]}>
          {activeProfile ? `Signed in as ${activeProfile.displayName}` : 'Quick access to your household.'}
        </Text>

        {/* Linked receivers list */}
        <Card style={dynamicBg(styles.card)}>
          <View style={styles.rowBetween}>
            <Text style={[styles.cardTitle, dynamicText(16)]}>Family care receivers</Text>
          </View>

          {loading ? (
            <ActivityIndicator style={{ marginTop: 12 }} />
          ) : receivers.length === 0 ? (
            <Text style={[styles.empty, dynamicText(14), highContrast && { color: '#333333' }]}>
              No care receivers found in this account. Please create one in profiles.
            </Text>
          ) : (
            <View style={{ gap: 14, marginTop: 12 }}>
              {receivers.map((r) => (
                <View key={r.link_id} style={dynamicBg([styles.receiverCard, r.has_active_help && styles.receiverCardHelp])}>
                  <View style={styles.receiverHeader}>
                    <View style={styles.avatar}>
                      <Text style={styles.avatarText}>
                        {r.receiver_name.charAt(0).toUpperCase()}
                      </Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.receiverName, dynamicText(16)]}>{r.receiver_name}</Text>
                      <Text style={[styles.receiverMeta, dynamicText(12), highContrast && { color: '#444' }]}>
                        Care receiver • {r.receiver_type ?? 'adult'}
                      </Text>
                    </View>
                    {r.has_active_help ? (
                      <View style={styles.statusBadgeHelp}>
                        <Text style={styles.statusBadgeTextHelp}>🚨 HELP REQUESTED</Text>
                      </View>
                    ) : (
                      <View style={styles.statusBadgeOk}>
                        <Text style={styles.statusBadgeTextOk}>● OK / Safe</Text>
                      </View>
                    )}
                  </View>

                  <View style={styles.actionsRow}>
                    <Pressable
                      style={({ pressed }) => [styles.actionButton, pressed && { opacity: 0.8 }, highContrast && { borderWidth: 1, borderColor: '#000' }]}
                      onPress={() => handlePingReceiver(r.receiver_profile_id)}
                    >
                      <Ionicons name="notifications-outline" size={16} color={Colors.primary} />
                      <Text style={[styles.actionButtonText, dynamicText(13)]}>Ping</Text>
                    </Pressable>

                    <Pressable
                      style={({ pressed }) => [styles.actionButton, pressed && { opacity: 0.8 }, highContrast && { borderWidth: 1, borderColor: '#000' }]}
                      onPress={() => handleChatWithReceiver(r.receiver_profile_id)}
                    >
                      <Ionicons name="chatbubble-ellipses-outline" size={16} color={Colors.primary} />
                      <Text style={[styles.actionButtonText, dynamicText(13)]}>Chat</Text>
                    </Pressable>

                    {r.has_active_help && r.help_request_id && (
                      <Pressable
                        style={({ pressed }) => [styles.actionButtonAcknowledge, pressed && { opacity: 0.8 }]}
                        onPress={() => r.help_request_id && handleAcknowledgeHelp(r.help_request_id)}
                      >
                        <Ionicons name="checkmark-circle-outline" size={16} color={Colors.white} />
                        <Text style={[styles.actionButtonAcknowledgeText, dynamicText(13)]}>Acknowledge</Text>
                      </Pressable>
                    )}
                  </View>
                </View>
              ))}
            </View>
          )}
        </Card>

        {/* Quick actions */}
        <Card style={dynamicBg(styles.card)}>
          <Text style={[styles.cardTitle, dynamicText(16)]}>Quick actions</Text>
          <View style={{ height: 8 }} />
          <Button title="Open chats" onPress={() => router.push('/(app)/caregiver/chats')} style={highContrast ? { borderWidth: 2, borderColor: '#000' } : undefined} />
          <View style={{ height: 10 }} />
          <Button
            title="VIEW ACTIVE ALERTS"
            variant="danger"
            onPress={() => router.push('/(app)/notifications')}
            style={highContrast ? { borderWidth: 2, borderColor: '#000' } : undefined}
          />
        </Card>
      </ScrollView>

      <EmergencyCall911 />
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
  empty: { color: Colors.muted, marginTop: 10, lineHeight: 20 },
  rowBetween: { flexDirection: 'row', alignItems: 'center', justifyRules: 'space-between' } as any,
  addBtn: {
    backgroundColor: Colors.primary,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 999,
  },
  addBtnText: { color: '#fff', fontWeight: '800', fontSize: 13 },
  receiverCard: {
    backgroundColor: Colors.white,
    borderColor: '#E2E8F0',
    borderWidth: 1,
    borderRadius: 20,
    padding: 16,
    gap: 12,
    shadowColor: '#0F172A',
    shadowOpacity: 0.04,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
  },
  receiverCardHelp: {
    borderColor: '#FCA5A5',
    backgroundColor: '#FEF2F2',
  },
  receiverHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  avatar: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: '#E0F2FE',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { color: '#0284C7', fontWeight: '900', fontSize: 18 },
  receiverName: { color: Colors.text, fontWeight: '800', fontSize: 17 },
  receiverMeta: { color: Colors.muted, fontSize: 13, marginTop: 1 },
  statusBadgeOk: {
    backgroundColor: '#DCFCE7',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 99,
  },
  statusBadgeTextOk: { color: '#16A34A', fontSize: 11, fontWeight: '900' },
  statusBadgeHelp: {
    backgroundColor: '#FEE2E2',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 99,
  },
  statusBadgeTextHelp: { color: '#DC2626', fontSize: 11, fontWeight: '900' },
  actionsRow: {
    flexDirection: 'row',
    gap: 10,
    borderTopWidth: 1,
    borderTopColor: '#F8FAFC',
    paddingTop: 14,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: '#F8FAFC',
    paddingVertical: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  actionButtonText: { color: Colors.text, fontSize: 13, fontWeight: '800' },
  actionButtonAcknowledge: {
    flex: 1.2,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: Colors.danger,
    paddingVertical: 10,
    borderRadius: 14,
    shadowColor: Colors.danger,
    shadowOpacity: 0.15,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 3 },
  },
  actionButtonAcknowledgeText: { color: Colors.white, fontSize: 13, fontWeight: '900' },
  nudgeBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: Colors.primary,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderRadius: 16,
    marginHorizontal: 16,
    marginTop: 8,
    marginBottom: 4,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  nudgeBannerSuccess: {
    backgroundColor: Colors.success,
  },
  nudgeBannerText: {
    color: '#fff',
    fontWeight: '800',
    fontSize: 14,
    flex: 1,
  },
  criticalAlertBlock: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: Colors.danger,
    paddingHorizontal: 18,
    paddingVertical: 18,
    borderRadius: 20,
    marginHorizontal: 16,
    marginTop: 10,
    marginBottom: 4,
    shadowColor: '#EF4444',
    shadowOpacity: 0.25,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 5,
    borderWidth: 2,
    borderColor: '#FECACA',
  },
  criticalAlertHeader: {
    color: '#fff',
    fontWeight: '900',
    fontSize: 16,
    letterSpacing: 0.5,
  },
  criticalAlertBody: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 14,
    marginTop: 3,
  },
  criticalAlertConfidence: {
    color: '#FEE2E2',
    fontWeight: '600',
    fontSize: 12,
    marginTop: 2,
  },
});
