import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, Pressable,
  useColorScheme, KeyboardAvoidingView, Platform,
  ActivityIndicator, Alert, ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { supabase } from '@/lib/supabase';
import { quantApi } from '@/lib/api';
import { usePortfolioStore } from '@/stores/portfolioStore';
import { usePortfolioFitCheck } from '@/hooks/usePortfolio';
import { ForecastPill } from '@/components/ui/ForecastPill';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing, Radius } from '@/constants/Theme';
import type { PortfolioContribution } from '@/lib/types';

export default function AddPositionScreen() {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const router = useRouter();

  const { activePortfolioId } = usePortfolioStore();
  const queryClient = useQueryClient();

  const [ticker, setTicker] = useState('');
  const [quantity, setQuantity] = useState('');
  const [costBasis, setCostBasis] = useState('');
  const [loading, setLoading] = useState(false);

  const sym = ticker.trim().toUpperCase();
  const qty = parseFloat(quantity);
  const cost = parseFloat(costBasis);
  const formComplete = !!sym && !isNaN(qty) && qty > 0 && !isNaN(cost) && cost > 0;

  const {
    mutate: checkFit,
    data: fitEnvelope,
    isPending: checkingFit,
    error: fitError,
    reset: resetFit,
  } = usePortfolioFitCheck(sym, activePortfolioId);

  const fitResult = fitEnvelope?.data;

  async function handleAdd() {
    if (!sym) return Alert.alert('Missing ticker', 'Enter a stock symbol like AAPL.');
    if (isNaN(qty) || qty <= 0) return Alert.alert('Invalid quantity', 'Enter a positive number of shares.');
    if (isNaN(cost) || cost <= 0) return Alert.alert('Invalid cost basis', 'Enter the average price you paid per share.');
    if (!activePortfolioId) return Alert.alert('No portfolio', 'No active portfolio found.');

    setLoading(true);
    try {
      const { error } = await supabase.from('positions').insert({
        portfolio_id: activePortfolioId,
        ticker: sym,
        quantity: qty,
        cost_basis: cost,
        opened_at: new Date().toISOString(),
      });
      if (error) throw error;

      quantApi.ingestTicker(sym).catch(() => null);

      await queryClient.invalidateQueries({ queryKey: ['snapshot', activePortfolioId] });
      await queryClient.invalidateQueries({ queryKey: ['positions', activePortfolioId] });

      router.back();
    } catch (e: unknown) {
      Alert.alert('Failed to add position', e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top', 'bottom']}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {/* Header */}
          <View style={styles.header}>
            <Pressable onPress={() => router.back()} hitSlop={12}>
              <Ionicons name="chevron-back" size={24} color={colors.textPrimary} />
            </Pressable>
            <Text style={[styles.title, { color: colors.textPrimary }]}>Add position</Text>
            <View style={{ width: 24 }} />
          </View>

          <View style={styles.form}>
            {/* Ticker */}
            <View style={styles.field}>
              <Text style={[styles.label, { color: colors.textSecondary }]}>Ticker symbol</Text>
              <TextInput
                style={[styles.input, { backgroundColor: colors.card, color: colors.textPrimary, borderColor: colors.border }]}
                placeholder="e.g. AAPL"
                placeholderTextColor={colors.textMuted}
                autoCapitalize="characters"
                autoCorrect={false}
                value={ticker}
                onChangeText={(t) => { setTicker(t.toUpperCase()); resetFit(); }}
              />
            </View>

            {/* Quantity */}
            <View style={styles.field}>
              <Text style={[styles.label, { color: colors.textSecondary }]}>Shares</Text>
              <TextInput
                style={[styles.input, { backgroundColor: colors.card, color: colors.textPrimary, borderColor: colors.border }]}
                placeholder="e.g. 10"
                placeholderTextColor={colors.textMuted}
                keyboardType="decimal-pad"
                value={quantity}
                onChangeText={setQuantity}
              />
            </View>

            {/* Cost basis */}
            <View style={styles.field}>
              <Text style={[styles.label, { color: colors.textSecondary }]}>Average cost per share ($)</Text>
              <TextInput
                style={[styles.input, { backgroundColor: colors.card, color: colors.textPrimary, borderColor: colors.border }]}
                placeholder="e.g. 150.00"
                placeholderTextColor={colors.textMuted}
                keyboardType="decimal-pad"
                value={costBasis}
                onChangeText={setCostBasis}
              />
            </View>

            {/* Preview */}
            {formComplete && (
              <View style={[styles.preview, { backgroundColor: colors.card, borderColor: colors.border }]}>
                <Text style={[styles.previewLine, { color: colors.textSecondary }]}>
                  <Text style={{ color: colors.accent, fontWeight: FontWeight.bold }}>{sym}</Text>
                  {' · '}{quantity} shares @ ${parseFloat(costBasis).toFixed(2)}
                </Text>
                <Text style={[styles.previewTotal, { color: colors.textPrimary }]}>
                  Total cost: ${(qty * cost).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </Text>
              </View>
            )}

            {/* Check portfolio fit */}
            {formComplete && !fitResult && !checkingFit && activePortfolioId && (
              <Pressable
                style={[styles.fitBtn, { borderColor: colors.accent }]}
                onPress={() => checkFit()}
              >
                <Ionicons name="git-network-outline" size={16} color={colors.accent} />
                <Text style={[styles.fitBtnText, { color: colors.accent }]}>Check portfolio fit</Text>
              </Pressable>
            )}

            {checkingFit && (
              <View style={[styles.fitLoading, { backgroundColor: colors.card }]}>
                <ActivityIndicator size="small" color={colors.accent} />
                <Text style={[styles.fitLoadingText, { color: colors.textSecondary }]}>
                  Checking portfolio fit…
                </Text>
              </View>
            )}

            {fitError && (
              <Text style={[styles.fitErrorText, { color: colors.textMuted }]}>
                Fit check unavailable — you can still add the position.
              </Text>
            )}

            {fitResult && (
              <FitResultCard result={fitResult} colors={colors} />
            )}
          </View>
        </ScrollView>

        {/* Footer */}
        <View style={[styles.footer, { borderTopColor: colors.border }]}>
          <Pressable
            style={[styles.btn, { backgroundColor: colors.accent, opacity: loading ? 0.7 : 1 }]}
            onPress={handleAdd}
            disabled={loading}
          >
            {loading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.btnText}>Add to portfolio</Text>}
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function FitResultCard({ result, colors }: { result: PortfolioContribution; colors: typeof Colors.dark }) {
  const recColor =
    result.recommendation === 'add' ? colors.green
    : result.recommendation === 'avoid' ? colors.red
    : result.recommendation === 'reduce' ? colors.amber
    : colors.textSecondary;

  const significantSectorDeltas = Object.entries(result.sector_delta).filter(([, v]) => Math.abs(v) >= 0.01);

  return (
    <View style={[fitStyles.card, { backgroundColor: colors.card, borderColor: recColor + '50' }]}>
      <View style={fitStyles.header}>
        <View style={[fitStyles.recBadge, { backgroundColor: recColor + '20' }]}>
          <Text style={[fitStyles.recText, { color: recColor }]}>
            {result.recommendation.toUpperCase()}
          </Text>
        </View>
        <ForecastPill />
      </View>

      <Text style={[fitStyles.reason, { color: colors.textPrimary }]}>{result.reason}</Text>

      {result.correlation_with_portfolio != null && (
        <Text style={[fitStyles.meta, { color: colors.textSecondary }]}>
          Portfolio correlation: {(result.correlation_with_portfolio * 100).toFixed(0)}%
        </Text>
      )}

      {significantSectorDeltas.map(([sector, delta]) => (
        <Text key={sector} style={[fitStyles.meta, { color: delta > 0 ? colors.amber : colors.green }]}>
          {sector} exposure: {delta > 0 ? '+' : ''}{(delta * 100).toFixed(1)}%
        </Text>
      ))}
    </View>
  );
}

const fitStyles = StyleSheet.create({
  card: { borderRadius: Radius.lg, padding: Spacing.lg, gap: Spacing.sm, borderWidth: 1 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  recBadge: { paddingHorizontal: Spacing.md, paddingVertical: 4, borderRadius: Radius.sm },
  recText: { fontSize: FontSize.xs, fontWeight: FontWeight.bold, letterSpacing: 0.5 },
  reason: { fontSize: FontSize.sm, lineHeight: 20 },
  meta: { fontSize: FontSize.xs },
});

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: Spacing.xl, gap: Spacing.xl, flexGrow: 1 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: Spacing.sm },
  title: { fontSize: FontSize.xl, fontWeight: FontWeight.bold },
  form: { gap: Spacing.xl },
  field: { gap: Spacing.sm },
  label: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold },
  input: {
    height: 52,
    borderRadius: Radius.md,
    borderWidth: 1,
    paddingHorizontal: Spacing.lg,
    fontSize: FontSize.lg,
  },
  preview: {
    padding: Spacing.lg,
    borderRadius: Radius.md,
    borderWidth: 1,
    gap: Spacing.xs,
  },
  previewLine: { fontSize: FontSize.sm },
  previewTotal: { fontSize: FontSize.md, fontWeight: FontWeight.semibold },
  fitBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1.5,
  },
  fitBtnText: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold },
  fitLoading: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, padding: Spacing.md, borderRadius: Radius.md },
  fitLoadingText: { fontSize: FontSize.sm },
  fitErrorText: { fontSize: FontSize.xs, textAlign: 'center' },
  footer: {
    padding: Spacing.xl,
    paddingBottom: 32,
    borderTopWidth: 1,
  },
  btn: {
    height: 52,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  btnText: { color: '#fff', fontSize: FontSize.md, fontWeight: FontWeight.semibold },
});
