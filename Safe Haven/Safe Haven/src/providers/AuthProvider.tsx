import type { Session } from '@supabase/supabase-js';
import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { supabase } from '../lib/supabase';

type AuthState = {
  isReady: boolean;
  session: Session | null;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session ?? null);
      setIsReady(true);
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession ?? null);
    });

    return () => {
      mounted = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  // Once signed in, save this device's push token so alerts can reach it
  // even when the app/phone is closed (no-op in Expo Go).
  useEffect(() => {
    const uid = session?.user?.id;
    if (!uid) return;
    import('../lib/notifications').then((m) => m.registerPushTokenForSession(uid));
  }, [session?.user?.id]);

  const value = useMemo(() => ({ isReady, session }), [isReady, session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}

