import React from 'react';
import { View, Text, StyleSheet, useColorScheme, Pressable } from 'react-native';
import { Colors } from '@/constants/Colors';
import { FontSize, Spacing } from '@/constants/Theme';

interface Props {
  asOf: string;              // ISO date-time string
  refreshIntervalMinutes?: number;
  onPress?: () => void;
}

function formatRelative(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function FreshnessStamp({ asOf, refreshIntervalMinutes = 60, onPress }: Props) {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];

  const staleMinutes = (Date.now() - new Date(asOf).getTime()) / 60_000;
  const isStale = staleMinutes > refreshIntervalMinutes;

  return (
    <Pressable onPress={onPress} style={styles.row}>
      {isStale && <View style={[styles.dot, { backgroundColor: colors.amber }]} />}
      <Text
        style={[styles.text, { color: isStale ? colors.amber : colors.textMuted }]}
        accessibilityLabel={`Data as of ${asOf}`}
      >
        as of {formatRelative(asOf)}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.xs },
  dot: { width: 6, height: 6, borderRadius: 3 },
  text: { fontSize: FontSize.xs },
});
