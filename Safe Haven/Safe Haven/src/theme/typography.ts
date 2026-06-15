export type TextPreset = 'h1' | 'h2' | 'h3' | 'body' | 'subtle' | 'label';

export const Typography = {
  h1: { fontSize: 34, fontWeight: '800' as const, letterSpacing: -0.6 },
  h2: { fontSize: 26, fontWeight: '800' as const, letterSpacing: -0.3 },
  h3: { fontSize: 20, fontWeight: '700' as const, letterSpacing: -0.2 },
  body: { fontSize: 16, fontWeight: '500' as const },
  subtle: { fontSize: 14, fontWeight: '500' as const },
  label: { fontSize: 13, fontWeight: '700' as const },
} as const;

