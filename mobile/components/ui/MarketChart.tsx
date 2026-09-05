import React, { useState } from 'react';
import { View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import Svg, { Path, Line, Text as SvgText } from 'react-native-svg';
import { useQuery } from '@tanstack/react-query';
import { useColorScheme } from 'react-native';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing, Radius } from '@/constants/Theme';

const QUANT_URL = process.env.EXPO_PUBLIC_QUANT_API_URL ?? 'http://localhost:8001';

const EXCHANGES = [
  { key: 'SP500',    label: 'S&P 500'  },
  { key: 'NASDAQ',   label: 'NASDAQ'   },
  { key: 'DOW',      label: 'Dow'      },
  { key: 'FTSE',     label: 'FTSE 100' },
  { key: 'NIKKEI',   label: 'Nikkei'   },
  { key: 'DAX',      label: 'DAX'      },
  { key: 'HANGSENG', label: 'Hang Seng'},
] as const;

const PERIODS = [
  { key: '5d',  label: '5D'  },
  { key: '1mo', label: '1M'  },
  { key: '3mo', label: '3M'  },
  { key: '6mo', label: '6M'  },
  { key: '1y',  label: '1Y'  },
] as const;

type ExchangeKey = typeof EXCHANGES[number]['key'];
type PeriodKey   = typeof PERIODS[number]['key'];

interface PricePoint  { date: string; close: number }
interface IndexData {
  key: string; name: string; exchange: string;
  latest: number; change_pct: number; prices: PricePoint[];
}

function buildPath(prices: PricePoint[], w: number, h: number): string {
  if (prices.length < 2) return '';
  const vals = prices.map((p) => p.close);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const pad = 4;
  const points = vals.map((v, i) => ({
    x: pad + (i / (vals.length - 1)) * (w - pad * 2),
    y: pad + (1 - (v - min) / range) * (h - pad * 2),
  }));
  return points.reduce((d, p, i) => d + (i === 0 ? `M${p.x},${p.y}` : ` L${p.x},${p.y}`), '');
}

function Sparkline({ prices, positive, width = 120, height = 48 }: {
  prices: PricePoint[]; positive: boolean; width?: number; height?: number;
}) {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const path = buildPath(prices, width, height);
  const color = positive ? colors.green : colors.red;
  return (
    <Svg width={width} height={height}>
      {path ? <Path d={path} stroke={color} strokeWidth={1.8} fill="none" strokeLinecap="round" strokeLinejoin="round" /> : null}
    </Svg>
  );
}

export function MarketChart() {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];

  const [selectedKeys, setSelectedKeys] = useState<ExchangeKey[]>(['SP500', 'NASDAQ', 'DOW']);
  const [period, setPeriod] = useState<PeriodKey>('1mo');

  const keysParam = selectedKeys.join(',');

  const { data, isLoading } = useQuery({
    queryKey: ['market-indices', keysParam, period],
    queryFn: async () => {
      const res = await fetch(`${QUANT_URL}/market/indices?keys=${keysParam}&period=${period}`);
      if (!res.ok) throw new Error('Failed to fetch market data');
      return res.json() as Promise<{ indices: IndexData[] }>;
    },
    staleTime: 5 * 60_000,
    enabled: selectedKeys.length > 0,
  });

  function toggleExchange(key: ExchangeKey) {
    setSelectedKeys((prev) =>
      prev.includes(key)
        ? prev.length > 1 ? prev.filter((k) => k !== key) : prev  // keep at least 1
        : [...prev, key]
    );
  }

  return (
    <View style={styles.root}>
      {/* Exchange selector */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipScroll} contentContainerStyle={styles.chipRow}>
        {EXCHANGES.map((ex) => {
          const active = selectedKeys.includes(ex.key);
          return (
            <Pressable
              key={ex.key}
              style={[
                styles.chip,
                { backgroundColor: active ? colors.accent : colors.card, borderColor: active ? colors.accent : colors.border },
              ]}
              onPress={() => toggleExchange(ex.key)}
            >
              <Text style={[styles.chipText, { color: active ? '#fff' : colors.textSecondary }]}>
                {ex.label}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>

      {/* Period selector */}
      <View style={styles.periodRow}>
        {PERIODS.map((p) => (
          <Pressable
            key={p.key}
            style={[
              styles.periodChip,
              { backgroundColor: period === p.key ? colors.accent + '22' : 'transparent' },
            ]}
            onPress={() => setPeriod(p.key)}
          >
            <Text style={[styles.periodText, { color: period === p.key ? colors.accent : colors.textMuted }]}>
              {p.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* Cards */}
      {isLoading && (
        <View style={styles.loadingRow}>
          <ActivityIndicator color={colors.accent} size="small" />
          <Text style={[styles.loadingText, { color: colors.textMuted }]}>Loading market data…</Text>
        </View>
      )}

      {!isLoading && data?.indices?.map((idx) => {
        const positive = idx.change_pct >= 0;
        const changeColor = positive ? colors.green : colors.red;
        return (
          <View key={idx.key} style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}>
            <View style={styles.cardLeft}>
              <Text style={[styles.cardName, { color: colors.textPrimary }]}>{idx.name}</Text>
              <Text style={[styles.cardExchange, { color: colors.textMuted }]}>{idx.exchange}</Text>
              <Text style={[styles.cardPrice, { color: colors.textPrimary }]}>
                {idx.latest.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </Text>
              <Text style={[styles.cardChange, { color: changeColor }]}>
                {positive ? '+' : ''}{idx.change_pct.toFixed(2)}%
              </Text>
            </View>
            <Sparkline prices={idx.prices} positive={positive} width={120} height={52} />
          </View>
        );
      })}

      {!isLoading && selectedKeys.length > 0 && !data?.indices?.length && (
        <Text style={[styles.loadingText, { color: colors.textMuted }]}>No data available.</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { gap: Spacing.sm },
  chipScroll: { marginHorizontal: -Spacing.lg },
  chipRow: { flexDirection: 'row', gap: Spacing.sm, paddingHorizontal: Spacing.lg },
  chip: {
    paddingHorizontal: Spacing.md,
    paddingVertical: 6,
    borderRadius: Radius.full,
    borderWidth: 1,
  },
  chipText: { fontSize: FontSize.xs, fontWeight: FontWeight.semibold },
  periodRow: { flexDirection: 'row', gap: Spacing.xs },
  periodChip: { paddingHorizontal: Spacing.md, paddingVertical: 4, borderRadius: Radius.sm },
  periodText: { fontSize: FontSize.xs, fontWeight: FontWeight.semibold },
  loadingRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, paddingVertical: Spacing.md },
  loadingText: { fontSize: FontSize.sm },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
    gap: Spacing.md,
  },
  cardLeft: { flex: 1, gap: 2 },
  cardName: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold },
  cardExchange: { fontSize: FontSize.xs },
  cardPrice: { fontSize: FontSize.md, fontWeight: FontWeight.bold, fontVariant: ['tabular-nums'], marginTop: 4 },
  cardChange: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold, fontVariant: ['tabular-nums'] },
});
