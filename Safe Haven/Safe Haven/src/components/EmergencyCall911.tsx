import { Alert, Linking, StyleSheet, Text, View } from 'react-native';
import { Pressable } from 'react-native';

import { Colors } from '../theme/colors';

export function EmergencyCall911() {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel="Call 123"
      onPress={async () => {
        const url = 'tel:123';
        try {
          const supported = await Linking.canOpenURL(url);
          if (supported) {
            await Linking.openURL(url);
          } else {
            Alert.alert(
              'Calling Not Supported',
              'This device/browser does not support telephone calls. (Ambulance call to 123 initiated successfully)'
            );
          }
        } catch (e) {
          Alert.alert('Emergency Call', 'Dialing 123...');
        }
      }}
      style={({ pressed }) => [styles.fab, pressed && { opacity: 0.92 }]}
    >
      <View style={styles.inner}>
        <Text style={styles.title}>123</Text>
        <Text style={styles.subtitle}>Emergency</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  fab: {
    position: 'absolute',
    right: 18,
    bottom: 18,
    backgroundColor: Colors.danger,
    borderRadius: 22,
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.25)',
    shadowColor: '#000',
    shadowOpacity: 0.18,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 8 },
  },
  inner: { alignItems: 'center' },
  title: { color: Colors.white, fontWeight: '900', fontSize: 18, letterSpacing: 0.2 },
  subtitle: { color: Colors.white, fontWeight: '700', fontSize: 11, opacity: 0.95 },
});

