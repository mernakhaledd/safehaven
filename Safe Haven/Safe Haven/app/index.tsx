import { Redirect } from 'expo-router';

export default function Index() {
  // Root route: AuthGate will redirect appropriately; keep a safe default.
  return <Redirect href="/(app)/profiles" />;
}

