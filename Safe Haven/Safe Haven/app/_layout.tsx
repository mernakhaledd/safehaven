import { Stack } from 'expo-router';

import { AuthGate } from '../src/components/AuthGate';
import { AuthProvider } from '../src/providers/AuthProvider';
import { ProfileProvider } from '../src/providers/ProfileProvider';

export default function RootLayout() {
  return (
    <AuthProvider>
      <ProfileProvider>
        <AuthGate>
          <Stack screenOptions={{ headerShown: false }}>
            <Stack.Screen name="(auth)" />
            <Stack.Screen name="(app)" />
          </Stack>
        </AuthGate>
      </ProfileProvider>
    </AuthProvider>
  );
}

