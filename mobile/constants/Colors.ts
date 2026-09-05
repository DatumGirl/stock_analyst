// Design token colors — mirrors CLAUDE.md §10.5
// Primary: deep blue accent; semantic green/red reserved for direction only.

const tints = {
  accent: '#1A56FF',
  green: '#22C55E',
  red: '#EF4444',
  amber: '#F59E0B',
  forecast: '#A78BFA',   // distinct violet tint for forecasted values
};

const dark = {
  background: '#0A0F1E',
  surface: '#111827',
  card: '#1C2333',
  border: '#2D3748',
  textPrimary: '#F9FAFB',
  textSecondary: '#9CA3AF',
  textMuted: '#6B7280',
};

const light = {
  background: '#F9FAFB',
  surface: '#FFFFFF',
  card: '#FFFFFF',
  border: '#E5E7EB',
  textPrimary: '#111827',
  textSecondary: '#6B7280',
  textMuted: '#9CA3AF',
};

export const Colors = {
  dark: { ...dark, ...tints },
  light: { ...light, ...tints },
};

export type ColorScheme = typeof Colors.dark;
