import type { ViewProps } from 'react-native';
import { StyleSheet, View } from 'react-native';

import { Colors } from '../../theme/colors';

export function Card({ style, ...props }: ViewProps) {
  return <View style={[styles.card, style]} {...props} />;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.card,
    borderColor: Colors.border,
    borderWidth: 1,
    borderRadius: 18,
    padding: 16,
  },
});

