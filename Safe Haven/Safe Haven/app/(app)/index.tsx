import { Redirect } from 'expo-router';

export default function AppIndex() {
  // Real routing is handled after profile selection.
  return <Redirect href="/(app)/profiles" />;
}

