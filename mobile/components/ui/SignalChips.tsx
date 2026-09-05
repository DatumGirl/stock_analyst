import React from 'react';
import { View, Text, StyleSheet, useColorScheme } from 'react-native';
import { Colors } from '@/constants/Colors';
import { FontSize, Spacing, Radius, FontWeight } from '@/constants/Theme';
import type { SignalDirection, TickerSignals } from '@/lib/types';

interface Props {
  signals: TickerSignals;
}

const LABELS: Record<keyof TickerSignals, string> = {
  fundamentals: 'Fundamentals',
  valuation: 'Valuation',
  momentum: 'Momentum',
};

function chipColors(dir: SignalDirection, scheme: 'light' | 'dark') {
  const c = Colors[scheme];
  if (dir === 'positive') return { bg: c.green + '22', fg: c.green };
  if (dir === 'negative') return { bg: c.red + '22', fg: c.red };
  return { bg: c.border, fg: c.textSecondary };
}

export function SignalChips({ signals }: Props) {
  const scheme = useColorScheme() ?? 'dark';

  return (
    <View style={styles.row}>
      {(Object.keys(LABELS) as (keyof TickerSignals)[]).map((key) => {
        const { bg, fg } = chipColors(signals[key], scheme);
        return (
          <View key={key} style={[styles.chip, { backgroundColor: bg }]}>
            <Text style={[styles.label, { color: fg }]}>{LABELS[key]}</Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: Spacing.sm, flexWrap: 'wrap' },
  chip: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: Radius.full,
  },
  label: { fontSize: FontSize.xs, fontWeight: FontWeight.semibold },
});
