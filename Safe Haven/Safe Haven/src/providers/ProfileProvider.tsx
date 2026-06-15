import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

export type Persona = 'care_giver' | 'care_receiver';
export type ReceiverType = 'infant' | 'toddler' | 'teen' | 'adult' | 'elder';

export type Profile = {
  id: string;
  displayName: string;
  persona: Persona;
  receiverType?: ReceiverType;
};

type ProfileState = {
  isLoading: boolean;
  profiles: Profile[];
  activeProfile: Profile | null;
  setActiveProfile: (p: Profile | null) => void;
  refreshProfiles: () => Promise<void>;
  textSize: 'normal' | 'large' | 'xl';
  updateTextSize: (val: 'normal' | 'large' | 'xl') => Promise<void>;
  highContrast: boolean;
  toggleContrast: (val: boolean) => Promise<void>;
};

const ProfileContext = createContext<ProfileState | null>(null);

const ACTIVE_PROFILE_ID_KEY = 'safehaven.activeProfileId';

export function ProfileProvider({ children }: { children: React.ReactNode }) {
  const [activeProfileId, setActiveProfileId] = useState<string | null>(null);
  const [activeProfile, setActiveProfile] = useState<Profile | null>(null);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [textSize, setTextSize] = useState<'normal' | 'large' | 'xl'>('normal');
  const [highContrast, setHighContrast] = useState(false);
  const lastUserIdRef = useRef<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const { secureStore } = await import('../lib/secureStore');
        const size = await secureStore.getItem('pref_textsize');
        if (size === 'normal' || size === 'large' || size === 'xl') {
          setTextSize(size);
        }
        const contrast = await secureStore.getItem('pref_contrast');
        if (contrast !== null) {
          setHighContrast(contrast === 'true');
        }
      } catch (e) {
        console.error('[Safe Haven] failed to load initial secureStore pref', e);
      }
    })();
  }, []);

  const updateTextSize = useCallback(async (val: 'normal' | 'large' | 'xl') => {
    const { secureStore } = await import('../lib/secureStore');
    setTextSize(val);
    await secureStore.setItem('pref_textsize', val);
  }, []);

  const toggleContrast = useCallback(async (val: boolean) => {
    const { secureStore } = await import('../lib/secureStore');
    setHighContrast(val);
    await secureStore.setItem('pref_contrast', String(val));
  }, []);

  // Lazy imports to avoid circular deps in early app startup.
  const refreshProfiles = useCallback(async () => {
    const { supabase } = await import('../lib/supabase');
    setIsLoading(true);
    try {
      // Get current user so we only load profiles owned by them,
      // not linked profiles from other users that RLS also makes visible.
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        setProfiles([]);
        return;
      }

      const { data, error } = await supabase
        .from('profiles')
        .select('id, display_name, persona, receiver_type')
        .eq('user_id', user.id)
        .order('created_at', { ascending: true });

      if (error) throw error;

      const next = (data ?? []).map((p) => ({
        id: p.id as string,
        displayName: p.display_name as string,
        persona: p.persona as Persona,
        receiverType: (p.receiver_type ?? undefined) as ReceiverType | undefined,
      }));

      setProfiles(next);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    let subHolder: { unsubscribe: () => void } | null = null;

    const init = async () => {
      const { supabase } = await import('../lib/supabase');
      const { secureStore } = await import('../lib/secureStore');

      const { data: sub } = supabase.auth.onAuthStateChange(async (_event, nextSession) => {
        if (!mounted) return;
        if (!nextSession) {
          // Signed out — clear everything including the persisted profile ID
          // so the next sign-in starts fresh (prevents stale profile from a previous user)
          try {
            await secureStore.removeItem(ACTIVE_PROFILE_ID_KEY);
          } catch (_) {}
          lastUserIdRef.current = null;
          setProfiles([]);
          setActiveProfile(null);
          setActiveProfileId(null);
          setIsLoading(false);
          return;
        }
        // Signed in — reload profiles for this user only if the user ID changed
        if (nextSession.user.id !== lastUserIdRef.current) {
          lastUserIdRef.current = nextSession.user.id;
          await refreshProfiles();
        }
        // Update active test session in DB for Pi routing
        supabase.from('active_test_session').upsert({ id: 1, user_id: nextSession.user.id }).then(({ error }) => {
          if (error) console.error('[Safe Haven] failed to update active_test_session', error);
        });
      });

      subHolder = sub.subscription;

      // Load profiles when session exists; also keep active profile id.
      const { data } = await supabase.auth.getSession();
      if (!mounted) return;

      if (!data.session) {
        setProfiles([]);
        setActiveProfile(null);
        setActiveProfileId(null);
        setIsLoading(false);
        return;
      }

      // Update active test session in DB for Pi routing
      supabase.from('active_test_session').upsert({ id: 1, user_id: data.session.user.id }).then(({ error }) => {
        if (error) console.error('[Safe Haven] failed to update active_test_session', error);
      });

      const savedId = await secureStore.getItem(ACTIVE_PROFILE_ID_KEY);
      if (!mounted) return;
      setActiveProfileId(savedId);

      if (data.session && data.session.user.id !== lastUserIdRef.current) {
        lastUserIdRef.current = data.session.user.id;
        await refreshProfiles();
      }
    };

    init();

    return () => {
      mounted = false;
      if (subHolder) {
        subHolder.unsubscribe();
      }
    };
  }, [refreshProfiles]);

  useEffect(() => {
    if (isLoading) return; // Prevent resetting active profile while reloading profiles
    if (!activeProfileId) {
      setActiveProfile(null);
      return;
    }
    const found = profiles.find((p) => p.id === activeProfileId);
    if (found) {
      setActiveProfile(found);
    } else {
      setActiveProfile(null);
    }
  }, [profiles, activeProfileId, isLoading]);

  const setActiveProfilePersisted = useCallback(async (p: Profile | null) => {
    const { secureStore } = await import('../lib/secureStore');
    if (!p) {
      await secureStore.removeItem(ACTIVE_PROFILE_ID_KEY);
      setActiveProfileId(null);
      setActiveProfile(null);
      return;
    }
    await secureStore.setItem(ACTIVE_PROFILE_ID_KEY, p.id);
    setActiveProfileId(p.id);
    setActiveProfile(p);
  }, []);

  const value = useMemo(
    () => ({
      isLoading,
      profiles,
      activeProfile,
      setActiveProfile: setActiveProfilePersisted,
      refreshProfiles,
      textSize,
      updateTextSize,
      highContrast,
      toggleContrast,
    }),
    [
      isLoading,
      profiles,
      activeProfile,
      setActiveProfilePersisted,
      refreshProfiles,
      textSize,
      updateTextSize,
      highContrast,
      toggleContrast,
    ],
  );

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function useProfile() {
  const ctx = useContext(ProfileContext);
  if (!ctx) throw new Error('useProfile must be used inside ProfileProvider');
  return ctx;
}

