import { createClient } from '@supabase/supabase-js';

import { env, requireEnv } from './env';
import { secureStore } from './secureStore';

const supabaseUrl = requireEnv(env.supabaseUrl, 'EXPO_PUBLIC_SUPABASE_URL');
const supabaseAnonKey = requireEnv(env.supabaseAnonKey, 'EXPO_PUBLIC_SUPABASE_ANON_KEY');

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    storage: {
      getItem: secureStore.getItem,
      setItem: secureStore.setItem,
      removeItem: secureStore.removeItem,
    },
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
});
