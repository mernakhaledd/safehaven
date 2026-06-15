export const env = {
  supabaseUrl: process.env.EXPO_PUBLIC_SUPABASE_URL,
  supabaseAnonKey: process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY,
} as const;

export function requireEnv(value: string | undefined, name: string): string {
  if (!value) {
    throw new Error(
      `Missing env var ${name}. Create a local env file and set EXPO_PUBLIC_SUPABASE_URL / EXPO_PUBLIC_SUPABASE_ANON_KEY.`,
    );
  }
  return value;
}

