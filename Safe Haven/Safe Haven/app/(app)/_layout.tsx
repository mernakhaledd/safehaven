import { Stack } from 'expo-router';

export default function AppLayout() {
  return (
    <Stack
      screenOptions={{
        headerTitle: 'Safe Haven',
        headerShadowVisible: false,
        animation: 'slide_from_right',
      }}
    />
  );
}
