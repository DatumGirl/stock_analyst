import React from 'react';
import { View, Text, StyleSheet, Pressable, useColorScheme } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '@/constants/Colors';
import { FontSize, Spacing, FontWeight } from '@/constants/Theme';

interface Props {
  type?: 'empty' | 'error' | 'stale' | 'offline';
  title: string;
  body?: string;
  actionLabel?: string;
  onAction?: () => void;
}

const TYPE_ICON: Record<string, keyof typeof Ionicons.glyphMap> = {
  empty: 'layers-outline',
  error: 'alert-circle-outline',
  stale: 'time-outline',
  offline: 'wifi-outline',
};

export function EmptyState({ type = 'empty', title, body, actionLabel, onAction }: Props) {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];

  return (
    <View style={styles.container}>
      <Ionicons name={TYPE_ICON[type]} size={40} color={colors.textMuted} />
      <Text style={[styles.title, { color: colors.textPrimary }]}>{title}</Text>
      {body && <Text style={[styles.body, { color: colors.textSecondary }]}>{body}</Text>}
      {actionLabel && onAction && (
        <Pressable
          onPress={onAction}
          style={[styles.button, { borderColor: colors.accent }]}
          accessibilityRole="button"
        >
          <Text style={[styles.buttonText, { color: colors.accent }]}>{actionLabel}</Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center', gap: Spacing.md, padding: Spacing.xxl },
  title: { fontSize: FontSize.lg, fontWeight: FontWeight.semibold, textAlign: 'center' },
  body: { fontSize: FontSize.sm, textAlign: 'center', lineHeight: 20 },
  button: { marginTop: Spacing.sm, paddingHorizontal: Spacing.xl, paddingVertical: Spacing.md, borderRadius: 999, borderWidth: 1 },
  buttonText: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold },
});
