import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable,
  useColorScheme, TextInput, ActivityIndicator,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useCompare } from '@/hooks/useTicker';
import { ForecastPill } from '@/components/ui/ForecastPill';
import { EmptyState } from '@/components/ui/EmptyState';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing, Radius } from '@/constants/Theme';

const MAX_TICKERS = 4;

const COMPARE_METRICS: Array<{ key: keyof any; label: string; format: (v: any) => string }> = [
  { key: 'revenue_growth', label: 'Revenue growth', format: (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—' },
  { key: 'pe', label: 'P/E', format: (v) => v ?? '—' },
  { key: 'fwd_pe', label: 'Fwd P/E', format: (v) => v ?? '—' },
  { key: 'gross_margin', label: 'Gross margin', format: (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—' },
  { key: 'roic', label: 'ROIC', format: (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—' },
  { key: 'debt_to_equity', label: 'Debt/Equity', format: (v) => v != null ? v.toFixed(2) : '—' },
  { key: 'momentum_score', label: 'Momentum', format: (v) => v != null ? `${v.toFixed(0)}/100` : '—' },
  { key: 'fair_value_gap_pct', label: 'Fair value gap', format: (v) => v != null ? `${(v * 100).toFixed(1)}%` : '—' },
];

export default function CompareScreen() {
  const { initial } = useLocalSearchParams<{ initial?: string }>();
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const router = useRouter();

  const [tickers, setTickers] = useState<string[]>(initial ? [initial] : []);
  const [input, setInput] = useState('');

  const { mutate: runCompare, data: result, isPending, error } = useCompare(tickers);

  function addTicker() {
    const t = input.trim().toUpperCase();
    if (!t || tickers.includes(t) || tickers.length >= MAX_TICKERS) return;
    setTickers([...tickers, t]);
    setInput('');
  }

  const analysis = result?.data;

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top', 'bottom']}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={8}>
          <Ionicons name="close" size={24} color={colors.textPrimary} />
        </Pressable>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Compare</Text>
        <View style={{ width: 24 }} />
      </View>

      {/* Ticker chips */}
      <View style={styles.chipRow}>
        {tickers.map((t) => (
          <Pressable
            key={t}
            style={[styles.tickerChip, { backgroundColor: colors.accent + '22', borderColor: colors.accent }]}
            onPress={() => setTickers(tickers.filter((x) => x !== t))}
          >
            <Text style={[styles.tickerChipText, { color: colors.accent }]}>{t}</Text>
            <Ionicons name="close" size={12} color={colors.accent} />
          </Pressable>
        ))}
        {tickers.length < MAX_TICKERS && (
          <View style={[styles.inputWrap, { backgroundColor: colors.card, borderColor: colors.border }]}>
            <TextInput
              style={[styles.tickerInput, { color: colors.textPrimary }]}
              placeholder="+ Add ticker"
              placeholderTextColor={colors.textMuted}
              autoCapitalize="characters"
              autoCorrect={false}
              value={input}
              onChangeText={setInput}
              onSubmitEditing={addTicker}
              returnKeyType="done"
            />
          </View>
        )}
      </View>

      <Pressable
        style={[
          styles.compareBtn,
          { backgroundColor: tickers.length >= 2 ? colors.accent : colors.border },
        ]}
        onPress={() => runCompare()}
        disabled={tickers.length < 2 || isPending}
      >
        {isPending
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.compareBtnText}>Compare {tickers.length} stocks</Text>
        }
      </Pressable>

      {error && (
        <EmptyState type="error" title="Comparison failed" body={error.message} actionLabel="Retry" onAction={() => runCompare()} />
      )}

      {analysis && (
        <ScrollView contentContainerStyle={styles.resultScroll} horizontal={false}>
          {/* Chief analyst summary */}
          <View style={[styles.summaryCard, { backgroundColor: colors.card }]}>
            <View style={styles.summaryHeader}>
              <Text style={[styles.summaryLabel, { color: colors.textMuted }]}>Chief Analyst</Text>
              <ForecastPill />
            </View>
            <Text style={[styles.summaryText, { color: colors.textPrimary }]}>
              {analysis.chief_analyst_summary}
            </Text>
          </View>

          {/* Comparison table (horizontal scroll) */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View>
              {/* Header row */}
              <View style={[styles.tableRow, { backgroundColor: colors.card }]}>
                <View style={styles.metricCol}>
                  <Text style={[styles.colHeader, { color: colors.textMuted }]}>Metric</Text>
                </View>
                {analysis.tickers.map((t) => (
                  <View key={t} style={styles.valueCol}>
                    <Text style={[styles.colHeader, { color: colors.accent }]}>{t}</Text>
                  </View>
                ))}
              </View>

              {/* Data rows */}
              {COMPARE_METRICS.map((metric, i) => (
                <View
                  key={metric.key as string}
                  style={[
                    styles.tableRow,
                    { backgroundColor: i % 2 === 0 ? colors.surface : colors.card },
                  ]}
                >
                  <View style={styles.metricCol}>
                    <Text style={[styles.metricText, { color: colors.textSecondary }]}>{metric.label}</Text>
                  </View>
                  {analysis.rows.map((row) => {
                    const value = (row as any)[metric.key as string];
                    const formatted = metric.format(value);
                    return (
                      <View key={row.ticker} style={styles.valueCol}>
                        <Text style={[styles.valueText, { color: colors.textPrimary }]}>{formatted}</Text>
                      </View>
                    );
                  })}
                </View>
              ))}
            </View>
          </ScrollView>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: Spacing.lg },
  title: { fontSize: FontSize.xl, fontWeight: FontWeight.bold },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm, paddingHorizontal: Spacing.lg },
  tickerChip: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.xs,
    paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm,
    borderRadius: Radius.full, borderWidth: 1,
  },
  tickerChipText: { fontSize: FontSize.sm, fontWeight: FontWeight.bold },
  inputWrap: { paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, borderRadius: Radius.full, borderWidth: 1 },
  tickerInput: { fontSize: FontSize.sm, minWidth: 80 },
  compareBtn: {
    margin: Spacing.lg,
    padding: Spacing.lg,
    borderRadius: Radius.lg,
    alignItems: 'center',
  },
  compareBtnText: { color: '#fff', fontSize: FontSize.md, fontWeight: FontWeight.semibold },
  resultScroll: { padding: Spacing.lg, gap: Spacing.lg, paddingBottom: 40 },
  summaryCard: { borderRadius: Radius.lg, padding: Spacing.lg, gap: Spacing.sm },
  summaryHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  summaryLabel: { fontSize: FontSize.xs, textTransform: 'uppercase', letterSpacing: 0.8 },
  summaryText: { fontSize: FontSize.md, lineHeight: 24 },
  tableRow: { flexDirection: 'row', alignItems: 'center' },
  metricCol: { width: 130, padding: Spacing.md, paddingRight: Spacing.lg },
  valueCol: { width: 90, padding: Spacing.md, alignItems: 'center' },
  colHeader: { fontSize: FontSize.xs, fontWeight: FontWeight.bold, textTransform: 'uppercase' },
  metricText: { fontSize: FontSize.sm },
  valueText: { fontSize: FontSize.sm, fontVariant: ['tabular-nums'] },
});
