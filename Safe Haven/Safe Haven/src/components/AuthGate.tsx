import { useRouter, useSegments } from 'expo-router';
import React, { useEffect } from 'react';

import { useAuth } from '../providers/AuthProvider';

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { isReady, session } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (!isReady) return;

    const inAuthGroup = segments[0] === '(auth)';

    if (!session && !inAuthGroup) {
      router.replace('/(auth)/sign-in');
      return;
    }

    if (session && inAuthGroup) {
      router.replace('/(app)/profiles');
    }
  }, [isReady, session, segments, router]);

  if (!isReady) return null;

  return <>{children}</>;
}

