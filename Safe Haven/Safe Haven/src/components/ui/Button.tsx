import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, type PressableProps } from 'react-native';

import { Colors } from '../../theme/colors';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';
type Size = 'md' | 'lg' | 'xl';

export function Button({
  title,
  left,
  variant = 'primary',
  size = 'lg',
  style,
  ...props
}: PressableProps & { title: string; left?: ReactNode; variant?: Variant; size?: Size }) {
  return (
    <Pressable
      accessibilityRole="button"
      style={({ pressed }) => {
        const resolvedStyle = typeof style === 'function' ? style({ pressed }) : style;
        return [
          styles.base,
          stylesByVariant[variant],
          stylesBySize[size],
          pressed && { opacity: 0.9, transform: [{ scale: 0.99 }] },
          props.disabled && { opacity: 0.5 },
          resolvedStyle,
        ];
      }}
      {...props}
    >
      {left}
      <Text style={[styles.text, textByVariant[variant]]}>{title}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    borderRadius: 16,
    borderWidth: 1,
  },
  text: {
    fontSize: 16,
    fontWeight: '800',
  },
});

const stylesByVariant = StyleSheet.create({
  primary: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  secondary: { backgroundColor: Colors.white, borderColor: Colors.border },
  danger: { backgroundColor: Colors.danger, borderColor: Colors.danger },
  ghost: { backgroundColor: 'transparent', borderColor: 'transparent' },
});

const textByVariant = StyleSheet.create({
  primary: { color: Colors.white },
  secondary: { color: Colors.text },
  danger: { color: Colors.white },
  ghost: { color: Colors.primary },
});

const stylesBySize = StyleSheet.create({
  md: { paddingVertical: 10, paddingHorizontal: 12 },
  lg: { paddingVertical: 12, paddingHorizontal: 14 },
  xl: { paddingVertical: 16, paddingHorizontal: 16, borderRadius: 18 },
});

