import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, RefreshControl,
  useColorScheme, Pressable,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '@/stores/authStore';
import { usePortfolioStore } from '@/stores/portfolioStore';
import { usePortfolioSnapshot, useWhatChanged, usePositions } from '@/hooks/usePortfolio';
import { ScoreRing } from '@/components/ui/ScoreRing';
import { DeltaLabel } from '@/components/ui/DeltaLabel';
import { MaterialityRow } from '@/components/ui/MaterialityRow';
import { FreshnessStamp } from '@/components/ui/FreshnessStamp';
import { SkeletonGroup } from '@/components/ui/SkeletonCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing, Radius } from '@/constants/Theme';

const PERIOD_OPTIONS = ['1D', '1W', '1M', 'YTD', '1Y'] as const;

export default function PortfolioScreen() {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const router = useRouter();

  const { user } = useAuthStore();
  const { portfolios, activePortfolioId, loadPortfolios, setActivePortfolio } = usePortfolioStore();

  const [activePeriod, setActivePeriod] = useState<(typeof PERIOD_OPTIONS)[number]>('1D');
  const [exposureTab, setExposureTab] = useState<'Sector' | 'Geography' | 'Theme' | 'Hidden'>('Sector');
  const [showSwitcher, setShowSwitcher] = useState(false);

  useEffect(() => {
    if (user) loadPortfolios(user.id);
  }, [user?.id]);

  const { data: snapshot, isLoading: snapLoading, refetch: refetchSnap } = usePortfolioSnapshot(activePortfolioId);
  const { data: changes, isLoading: changesLoading } = useWhatChanged(activePortfolioId);
  const { data: positions } = usePositions(activePortfolioId);

  const isLoading = snapLoading || changesLoading;

  const exposures = snapshot?.exposures?.[exposureTab.toLowerCase() as 'sector' | 'geography' | 'theme'];

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={isLoading} onRefresh={refetchSnap} tintColor={colors.accent} />}
        showsVerticalScrollIndicator={false}
        scrollEnabled={!showSwitcher}
      >
        {/* Header */}
        <View style={styles.nav}>
          {/* Portfolio name / switcher */}
          <Pressable style={styles.namePill} onPress={() => setShowSwitcher(true)}>
            <Text style={[styles.navTitle, { color: colors.textPrimary }]} numberOfLines={1}>
              {portfolios.find((p) => p.id === activePortfolioId)?.name ?? 'Portfolio'}
            </Text>
            {portfolios.length > 0 && (
              <Ionicons name="chevron-down" size={16} color={colors.textSecondary} style={{ marginTop: 2 }} />
            )}
          </Pressable>

          <View style={{ flexDirection: 'row', alignItems: 'center', gap: Spacing.sm }}>
            {snapshot && <FreshnessStamp asOf={snapshot.created_at} />}
            <Pressable
              onPress={() => router.push('/add-position')}
              hitSlop={12}
              style={[styles.iconBtn, { backgroundColor: colors.card, borderColor: colors.border }]}
            >
              <Ionicons name="add" size={18} color={colors.accent} />
            </Pressable>
          </View>
        </View>


        {/* Period selector */}
        <View style={styles.periodRow}>
          {PERIOD_OPTIONS.map((p) => (
            <Pressable
              key={p}
              style={[
                styles.periodChip,
                { backgroundColor: activePeriod === p ? colors.accent : 'transparent', borderColor: colors.border },
              ]}
              onPress={() => setActivePeriod(p)}
            >
              <Text style={[styles.periodText, { color: activePeriod === p ? '#fff' : colors.textSecondary }]}>{p}</Text>
            </Pressable>
          ))}
        </View>

        {isLoading && <SkeletonGroup count={3} />}

        {!isLoading && !snapshot && (
          <EmptyState
            type="empty"
            title="No portfolio data"
            body="Add positions to start tracking your portfolio."
            actionLabel="Add positions"
            onAction={() => router.push('/add-position')}
          />
        )}

        {snapshot && (
          <>
            {/* Value + change */}
            <View style={[styles.valueCard, { backgroundColor: colors.card }]}>
              <Text style={[styles.valueLabel, { color: colors.textSecondary }]}>Total value</Text>
              <DeltaLabel
                value={`$${parseFloat(snapshot.total_value).toLocaleString()}`}
                changePct={snapshot.day_return}
                size="lg"
              />
            </View>

            {/* Health card */}
            <View style={[styles.healthCard, { backgroundColor: colors.card }]}>
              <View style={styles.healthTop}>
                <ScoreRing score={snapshot.health_score} size={72} label="Health" />
                <View style={styles.subScores}>
                  {[
                    { label: 'Diversification', score: snapshot.diversification_score },
                    { label: 'Risk', score: snapshot.risk_score },
                    { label: 'Quality', score: snapshot.quality_score },
                  ].map((s) => (
                    <View key={s.label} style={styles.subScore}>
                      <Text style={[styles.subScoreLabel, { color: colors.textSecondary }]}>{s.label}</Text>
                      <View style={[styles.subBar, { backgroundColor: colors.border }]}>
                        <View style={[styles.subFill, { width: `${s.score}%`, backgroundColor: colors.accent }]} />
                      </View>
                    </View>
                  ))}
                </View>
              </View>
            </View>

            {/* What changed */}
            {changes && changes.length > 0 && (
              <>
                <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>What changed</Text>
                <View style={styles.list}>
                  {changes.slice(0, 5).map((c) => (
                    <MaterialityRow
                      key={c.id}
                      type={c.change_type as any}
                      title={c.summary}
                      reason={c.detail ?? ''}
                      tickers={c.ticker ? [c.ticker] : []}
                      onPress={() => c.ticker && router.push(`/ticker/${c.ticker}`)}
                    />
                  ))}
                </View>
              </>
            )}

            {/* Exposures */}
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Exposure</Text>
            <View style={[styles.exposureCard, { backgroundColor: colors.card }]}>
              {/* Tab row */}
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabScroll}>
                {(['Sector', 'Geography', 'Theme', 'Hidden'] as const).map((tab) => (
                  <Pressable
                    key={tab}
                    style={[
                      styles.exposureTab,
                      { borderBottomColor: exposureTab === tab ? colors.accent : 'transparent' },
                    ]}
                    onPress={() => setExposureTab(tab)}
                  >
                    <Text style={[styles.exposureTabText, { color: exposureTab === tab ? colors.accent : colors.textSecondary }]}>
                      {tab}
                    </Text>
                  </Pressable>
                ))}
              </ScrollView>

              {exposures && Object.entries(exposures).map(([name, pct]) => (
                <View key={name} style={styles.exposureRow}>
                  <Text style={[styles.exposureName, { color: colors.textPrimary }]} numberOfLines={1}>{name}</Text>
                  <View style={[styles.exposureBar, { backgroundColor: colors.border }]}>
                    <View style={[styles.exposureFill, { width: `${Math.min((pct as number) * 100, 100)}%`, backgroundColor: colors.accent }]} />
                  </View>
                  <Text style={[styles.exposurePct, { color: colors.textSecondary }]}>
                    {((pct as number) * 100).toFixed(0)}%
                  </Text>
                </View>
              ))}

              {exposureTab === 'Hidden' && snapshot.exposures?.hidden?.map((h, i) => (
                <View key={i} style={[styles.hiddenRow, { backgroundColor: colors.amber + '11' }]}>
                  <Ionicons name="warning-outline" size={14} color={colors.amber} />
                  <Text style={[styles.hiddenText, { color: colors.textSecondary }]}>
                    <Text style={{ fontWeight: FontWeight.semibold, color: colors.textPrimary }}>{h.tickers.join(', ')}</Text> share {h.dependency}
                  </Text>
                </View>
              ))}
            </View>

            {/* Holdings */}
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Holdings</Text>
            <View style={[styles.holdingsCard, { backgroundColor: colors.card }]}>
              {positions?.map((pos) => (
                <Pressable
                  key={pos.id}
                  style={styles.holdingRow}
                  onPress={() => router.push(`/ticker/${pos.ticker}`)}
                >
                  <View style={[styles.tickerBadge, { backgroundColor: colors.accent + '22' }]}>
                    <Text style={[styles.tickerText, { color: colors.accent }]}>{pos.ticker}</Text>
                  </View>
                  <View style={styles.holdingInfo}>
                    <Text style={[styles.holdingQty, { color: colors.textSecondary }]}>
                      {pos.quantity} shares @ ${parseFloat(pos.cost_basis).toFixed(2)}
                    </Text>
                  </View>
                  <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
                </Pressable>
              ))}

              {(!positions || positions.length === 0) && (
                <Text style={[styles.noHoldings, { color: colors.textMuted }]}>No holdings yet</Text>
              )}
            </View>
          </>
        )}
      </ScrollView>

      {/* Portfolio switcher — inline overlay, no Modal */}
      {showSwitcher && (
        <View style={StyleSheet.absoluteFillObject}>
          <Pressable style={styles.overlay} onPress={() => setShowSwitcher(false)} />
          <View style={[styles.sheet, { backgroundColor: colors.card }]}>
            <View style={[styles.sheetHandle, { backgroundColor: colors.border }]} />
            <Text style={[styles.sheetTitle, { color: colors.textPrimary }]}>Your portfolios</Text>

            {portfolios.map((p) => (
              <Pressable
                key={p.id}
                style={[
                  styles.sheetRow,
                  { borderColor: colors.border, backgroundColor: p.id === activePortfolioId ? colors.accent + '12' : 'transparent' },
                ]}
                onPress={() => { setActivePortfolio(p.id); setShowSwitcher(false); }}
              >
                <Text style={[styles.sheetRowName, { flex: 1, color: p.id === activePortfolioId ? colors.accent : colors.textPrimary }]}>
                  {p.name}
                </Text>
                {p.id === activePortfolioId && <Ionicons name="checkmark-circle" size={20} color={colors.accent} />}
              </Pressable>
            ))}

            <Pressable
              style={[styles.sheetNewBtn, { borderColor: colors.accent }]}
              onPress={() => { setShowSwitcher(false); router.push('/create-portfolio'); }}
            >
              <Ionicons name="add-circle-outline" size={18} color={colors.accent} />
              <Text style={[styles.sheetNewText, { color: colors.accent }]}>New portfolio</Text>
            </Pressable>
          </View>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: Spacing.lg, gap: Spacing.lg, paddingBottom: 40 },
  nav: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  namePill: { flexDirection: 'row', alignItems: 'center', gap: 4, flexShrink: 1, maxWidth: '65%' },
  iconBtn: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center', borderWidth: 1 },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)' },
  sheet: { borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: Spacing.xl, paddingBottom: 48, gap: Spacing.sm },
  sheetHandle: { width: 36, height: 4, borderRadius: 2, alignSelf: 'center', marginBottom: Spacing.md },
  sheetTitle: { fontSize: FontSize.lg, fontWeight: FontWeight.bold, marginBottom: Spacing.sm },
  sheetRow: { flexDirection: 'row', alignItems: 'center', padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1, gap: Spacing.sm },
  sheetRowName: { fontSize: FontSize.md, fontWeight: FontWeight.semibold },
  sheetNewBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.sm, padding: Spacing.md, borderRadius: Radius.md, borderWidth: 1.5, marginTop: Spacing.sm },
  sheetNewText: { fontSize: FontSize.md, fontWeight: FontWeight.semibold },
  navTitle: { fontSize: FontSize.xxl, fontWeight: FontWeight.bold },
  periodRow: { flexDirection: 'row', gap: Spacing.sm },
  periodChip: { paddingHorizontal: Spacing.md, paddingVertical: Spacing.xs, borderRadius: Radius.full, borderWidth: 1 },
  periodText: { fontSize: FontSize.xs, fontWeight: FontWeight.semibold },
  list: { gap: Spacing.sm },
  valueCard: { borderRadius: Radius.lg, padding: Spacing.lg, gap: Spacing.xs },
  valueLabel: { fontSize: FontSize.sm },
  healthCard: { borderRadius: Radius.lg, padding: Spacing.lg },
  healthTop: { flexDirection: 'row', alignItems: 'center', gap: Spacing.xl },
  subScores: { flex: 1, gap: Spacing.md },
  subScore: { gap: Spacing.xs },
  subScoreLabel: { fontSize: FontSize.xs },
  subBar: { height: 4, borderRadius: 2, overflow: 'hidden' },
  subFill: { height: 4, borderRadius: 2 },
  sectionTitle: { fontSize: FontSize.lg, fontWeight: FontWeight.semibold, marginTop: Spacing.sm },
  exposureCard: { borderRadius: Radius.lg, overflow: 'hidden' },
  tabScroll: { borderBottomWidth: 1 },
  exposureTab: { paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, borderBottomWidth: 2 },
  exposureTabText: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold },
  exposureRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, padding: Spacing.md },
  exposureName: { width: 100, fontSize: FontSize.sm },
  exposureBar: { flex: 1, height: 6, borderRadius: 3, overflow: 'hidden' },
  exposureFill: { height: 6, borderRadius: 3 },
  exposurePct: { width: 36, textAlign: 'right', fontSize: FontSize.xs, fontVariant: ['tabular-nums'] },
  hiddenRow: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.sm, padding: Spacing.md },
  hiddenText: { flex: 1, fontSize: FontSize.sm, lineHeight: 20 },
  holdingsCard: { borderRadius: Radius.lg, overflow: 'hidden' },
  holdingRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, padding: Spacing.md },
  tickerBadge: { paddingHorizontal: Spacing.sm, paddingVertical: Spacing.xs, borderRadius: Radius.sm },
  tickerText: { fontSize: FontSize.sm, fontWeight: FontWeight.bold },
  holdingInfo: { flex: 1 },
  holdingQty: { fontSize: FontSize.xs },
  noHoldings: { padding: Spacing.xl, textAlign: 'center', fontSize: FontSize.sm },
});
