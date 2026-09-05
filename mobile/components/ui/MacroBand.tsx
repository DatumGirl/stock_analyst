import React from 'react';
import { View, Text, ScrollView, StyleSheet, ActivityIndicator } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { useColorScheme } from 'react-native';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing, Radius } from '@/constants/Theme';
import type { MacroItem } from '@/lib/types';

const QUANT_URL = process.env.EXPO_PUBLIC_QUANT_API_URL ?? 'http://localhost:8001';

function formatValue(item: MacroItem): string {
  const v = item.value;
  const prefix = item.unit === '$' ? '$' : '';
  const suffix = item.unit !== '$' ? item.unit : '';
  const decimals = item.unit === '%' ? 2 : v >= 1000 ? 0 : 2;
  return `${prefix}${v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}${suffix}`;
}

export function MacroBand() {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];

  const { data, isLoading } = useQuery({
    queryKey: ['macro-band'],
    queryFn: async () => {
      const res = await fetch(`${QUANT_URL}/market/macro`);
      if (!res.ok) throw new Error('macro unavailable');
      return res.json() as Promise<{ items: MacroItem[]; as_of: string }>;
    },
    staleTime: 5 * 60_000,
    retry: 0,
  });

  if (isLoading) {
    return (
      <View style={styles.loadingRow}>
        <ActivityIndicator size="small" color={colors.textMuted} />
      </View>
    );
  }

  if (!data?.items?.length) return null;

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      style={styles.scroll}
      contentContainerStyle={styles.row}
      scrollsToTop={false}
      directionalLockEnabled={true}
    >
      {data.items.map((item) => {
        const positive = (item.change_pct ?? 0) >= 0;
        const changeColor = item.change_pct === null
          ? colors.textMuted
          : positive ? colors.green : colors.red;
        return (
          <View
            key={item.key}
            style={[styles.chip, { backgroundColor: colors.card, borderColor: colors.border }]}
          >
            <Text style={[styles.label, { color: colors.textMuted }]}>{item.label}</Text>
            <Text style={[styles.value, { color: colors.textPrimary }]}>{formatValue(item)}</Text>
            {item.change_pct !== null && (
              <Text style={[styles.change, { color: changeColor }]}>
                {positive ? '+' : ''}{item.change_pct.toFixed(2)}%
              </Text>
            )}
          </View>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  loadingRow: { height: 20, alignItems: 'center', justifyContent: 'center' },
  scroll: { marginHorizontal: -Spacing.lg },
  row: { flexDirection: 'row', gap: Spacing.sm, paddingHorizontal: Spacing.lg },
  chip: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.md,
    borderWidth: 1,
    gap: 2,
    minWidth: 80,
  },
  label: { fontSize: 10, fontWeight: FontWeight.semibold, textTransform: 'uppercase', letterSpacing: 0.5 },
  value: { fontSize: FontSize.sm, fontWeight: FontWeight.bold, fontVariant: ['tabular-nums'] },
  change: { fontSize: 10, fontVariant: ['tabular-nums'] },
});
