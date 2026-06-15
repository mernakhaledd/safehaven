import type { ViewProps } from 'react-native';
import { StyleSheet, View } from 'react-native';

import { Colors } from '../../theme/colors';
import { Spacing } from '../../theme/spacing';

export function Screen({ style, ...props }: ViewProps) {
  return <View style={[styles.screen, style]} {...props} />;
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: Colors.bg,
    padding: Spacing.xl,
  },
});

