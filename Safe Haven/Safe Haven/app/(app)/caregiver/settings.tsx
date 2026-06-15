import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from 'react-native';

import { Button } from '../../../src/components/ui/Button';
import { Card } from '../../../src/components/ui/Card';
import { Screen } from '../../../src/components/ui/Screen';
import { supabase } from '../../../src/lib/supabase';
import { secureStore } from '../../../src/lib/secureStore';
import { useProfile } from '../../../src/providers/ProfileProvider';
import { useAuth } from '../../../src/providers/AuthProvider';
import { Colors } from '../../../src/theme/colors';

export default function CaregiverSettings() {
  const { session } = useAuth();
  const { activeProfile, textSize, updateTextSize, highContrast, toggleContrast } = useProfile();
  const [pushEnabled, setPushEnabled] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [batteryEnabled, setBatteryEnabled] = useState(true);

  // PIN security states
  const [pinEnabled, setPinEnabled] = useState(false);
  const [pinCode, setPinCode] = useState('1234');

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
    (async () => {
      try {
        const push = await secureStore.getItem('pref_push');
        if (push !== null) setPushEnabled(push === 'true');
        const sound = await secureStore.getItem('pref_sound');
        if (sound !== null) setSoundEnabled(sound === 'true');
        const battery = await secureStore.getItem('pref_battery');
        if (battery !== null) setBatteryEnabled(battery === 'true');

        const pin = await secureStore.getItem('pref_pin_enabled');
        if (pin !== null) setPinEnabled(pin === 'true');
        const code = await secureStore.getItem('pref_pin_code');
        if (code !== null) setPinCode(code);
      } catch (e) {
        console.error('[Safe Haven] failed to load preferences', e);
      }
    })();
  }, []);

  async function togglePush(val: boolean) {
    setPushEnabled(val);
    await secureStore.setItem('pref_push', String(val));
  }

  async function toggleSound(val: boolean) {
    setSoundEnabled(val);
    await secureStore.setItem('pref_sound', String(val));
  }

  async function toggleBattery(val: boolean) {
    setBatteryEnabled(val);
    await secureStore.setItem('pref_battery', String(val));
  }

  async function togglePin(val: boolean) {
    setPinEnabled(val);
    await secureStore.setItem('pref_pin_enabled', String(val));
  }

  async function changePinCode(val: string) {
    const clean = val.replace(/[^0-9]/g, '').slice(0, 4);
    setPinCode(clean);
    await secureStore.setItem('pref_pin_code', clean);
  }

  async function onSignOut() {
    try {
      console.log('[Safe Haven] Signing out caregiver...');
      // Clear active profile from secure store BEFORE signing out
      // so the next sign-in always starts at the profile picker
      const { secureStore } = await import('../../../src/lib/secureStore');
      await secureStore.removeItem('safehaven.activeProfileId');
      await supabase.auth.signOut();
    } catch (e) {
      console.error('[Safe Haven] signout error', e);
    }
    router.replace('/(auth)/sign-in');
  }

  return (
    <Screen style={highContrast ? { backgroundColor: '#ffffff' } : undefined}>
      <ScrollView contentContainerStyle={{ gap: 14, paddingBottom: 40 }}>
        <Text style={[styles.title, dynamicText(26)]}>Settings</Text>
        <Text style={[styles.subtitle, dynamicText(14), highContrast && { color: '#333333' }]}>
          {activeProfile ? `Profile: ${activeProfile.displayName}` : 'Configure your preferences.'}
        </Text>

        {/* Notifications Section */}
        <Card style={dynamicBg(styles.card)}>
          <Text style={[styles.cardHeader, dynamicText(16)]}>Notification Settings</Text>
          <View style={styles.divider} />
          
          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.rowTitle, dynamicText(15)]}>Push Notifications</Text>
              <Text style={[styles.rowSubtitle, dynamicText(12), highContrast && { color: '#444' }]}>Receive warnings on falls and emergency gestures.</Text>
            </View>
            <Switch
              value={pushEnabled}
              onValueChange={togglePush}
              trackColor={{ true: Colors.primary }}
            />
          </View>

          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.rowTitle, dynamicText(15)]}>Emergency Alarm Sounds</Text>
              <Text style={[styles.rowSubtitle, dynamicText(12), highContrast && { color: '#444' }]}>Play a loud alarm sound on critical alerts.</Text>
            </View>
            <Switch
              value={soundEnabled}
              onValueChange={toggleSound}
              trackColor={{ true: Colors.primary }}
            />
          </View>

          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.rowTitle, dynamicText(15)]}>Device Low Battery Alerts</Text>
              <Text style={[styles.rowSubtitle, dynamicText(12), highContrast && { color: '#444' }]}>Notify when edge devices or cameras run low.</Text>
            </View>
            <Switch
              value={batteryEnabled}
              onValueChange={toggleBattery}
              trackColor={{ true: Colors.primary }}
            />
          </View>
        </Card>

        {/* Security Preferences Section */}
        <Card style={dynamicBg(styles.card)}>
          <Text style={[styles.cardHeader, dynamicText(16)]}>Security Preferences</Text>
          <View style={styles.divider} />
          
          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.rowTitle, dynamicText(15)]}>Require PIN Lock</Text>
              <Text style={[styles.rowSubtitle, dynamicText(12), highContrast && { color: '#444' }]}>
                Require 4-digit PIN authentication before unlocking door or viewing cameras.
              </Text>
            </View>
            <Switch
              value={pinEnabled}
              onValueChange={togglePin}
              trackColor={{ true: Colors.primary }}
            />
          </View>

          {pinEnabled && (
            <View style={{ gap: 6, marginTop: 4 }}>
              <Text style={[styles.rowTitle, dynamicText(14)]}>Set 4-Digit Passcode PIN</Text>
              <TextInput
                style={[
                  styles.pinInput,
                  highContrast && { backgroundColor: '#fff', color: '#000', borderWidth: 1, borderColor: '#000' }
                ]}
                value={pinCode}
                onChangeText={changePinCode}
                keyboardType="number-pad"
                maxLength={4}
                secureTextEntry
                placeholder="Enter 4 digits"
              />
            </View>
          )}
        </Card>

        {/* Accessibility Section */}
        <Card style={dynamicBg(styles.card)}>
          <Text style={[styles.cardHeader, dynamicText(16)]}>Accessibility Preferences</Text>
          <View style={styles.divider} />

          <View style={{ gap: 8, paddingVertical: 4 }}>
            <Text style={[styles.rowTitle, dynamicText(15)]}>Text Size Scaling</Text>
            <View style={styles.segmentedControl}>
              {(['normal', 'large', 'xl'] as const).map((size) => (
                <Pressable
                  key={size}
                  style={[styles.segmentBtn, textSize === size && styles.segmentBtnActive]}
                  onPress={() => updateTextSize(size)}
                >
                  <Text style={[styles.segmentBtnText, textSize === size && styles.segmentBtnTextActive, dynamicText(12)]}>
                    {size.toUpperCase()}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>

          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={[styles.rowTitle, dynamicText(15)]}>High Contrast Mode</Text>
              <Text style={[styles.rowSubtitle, dynamicText(12), highContrast && { color: '#444' }]}>Enhance contrast to improve general visibility.</Text>
            </View>
            <Switch
              value={highContrast}
              onValueChange={toggleContrast}
              trackColor={{ true: Colors.primary }}
            />
          </View>
        </Card>

        {/* Profile Info and Sign Out */}
        <Card style={dynamicBg({ gap: 10 })}>
          <Text style={[styles.cardHeader, dynamicText(16)]}>Account Actions</Text>
          <Button title="Sign out" variant="secondary" onPress={onSignOut} />
        </Card>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 26, fontWeight: '900', color: Colors.text },
  subtitle: { color: Colors.muted, marginTop: 2, marginBottom: 8 },
  card: { gap: 12 },
  cardHeader: { fontSize: 16, fontWeight: '900', color: Colors.text },
  divider: { height: 1, backgroundColor: '#F1F5F9', marginVertical: 2 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 4,
    gap: 12,
  },
  rowTitle: { fontSize: 15, fontWeight: '800', color: Colors.text },
  rowSubtitle: { fontSize: 12, color: Colors.muted, marginTop: 2, lineHeight: 16 },
  pinInput: {
    backgroundColor: '#F1F5F9',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    color: Colors.text,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    letterSpacing: 4,
    textAlign: 'center',
    width: 120,
    fontWeight: 'bold',
  },
  segmentedControl: {
    flexDirection: 'row',
    backgroundColor: '#F1F5F9',
    borderRadius: 10,
    padding: 3,
    marginTop: 6,
  },
  segmentBtn: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 8,
  },
  segmentBtnActive: {
    backgroundColor: Colors.white,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 3,
    shadowOffset: { width: 0, height: 1 },
  },
  segmentBtnText: {
    fontSize: 12,
    fontWeight: '800',
    color: Colors.muted,
  },
  segmentBtnTextActive: {
    color: Colors.primary,
  },
});

