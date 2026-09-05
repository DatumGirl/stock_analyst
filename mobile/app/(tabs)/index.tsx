import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, RefreshControl,
  useColorScheme, Pressable,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '@/stores/authStore';
import { usePortfolioStore } from '@/stores/portfolioStore';
import { useBrief } from '@/hooks/useBrief';
import { ScoreRing } from '@/components/ui/ScoreRing';
import { DeltaLabel } from '@/components/ui/DeltaLabel';
import { MaterialityRow } from '@/components/ui/MaterialityRow';
import { ActionPill } from '@/components/ui/ActionPill';
import { FreshnessStamp } from '@/components/ui/FreshnessStamp';
import { SkeletonGroup } from '@/components/ui/SkeletonCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { MarketChart } from '@/components/ui/MarketChart';
import { MacroBand } from '@/components/ui/MacroBand';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing, Radius } from '@/constants/Theme';
import type { CatalystType, Sentiment } from '@/lib/types';

const CATALYST_ICON: Record<CatalystType, string> = {
  earnings: 'bar-chart-outline',
  filing: 'document-text-outline',
  fda: 'medkit-outline',
  macro: 'globe-outline',
  dividend: 'cash-outline',
  guidance: 'trending-up-outline',
  other: 'information-circle-outline',
};

export default function TodayScreen() {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const router = useRouter();

  const { activePortfolioId } = usePortfolioStore();
  const { data, isLoading, error, refetch, isFetching } = useBrief(activePortfolioId);
  const brief = data?.data;

  const pctColor = (v: number) => (v >= 0 ? colors.green : colors.red);

  function impactColor(impact: Sentiment): string {
    if (impact === 'positive') return colors.green;
    if (impact === 'negative') return colors.red;
    return colors.textSecondary;
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={isFetching} onRefresh={refetch} tintColor={colors.accent} />}
        showsVerticalScrollIndicator={false}
        directionalLockEnabled={true}
        alwaysBounceVertical={true}
      >
        {/* Nav bar */}
        <View style={styles.nav}>
          <Text style={[styles.navTitle, { color: colors.textPrimary }]}>Today</Text>
          {data?.as_of && <FreshnessStamp asOf={data.as_of} refreshIntervalMinutes={10} />}
        </View>

        {/* Macro band — key rates, VIX, DXY */}
        <MacroBand />

        {/* Market overview */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Markets</Text>
        <MarketChart />

        {isLoading && <SkeletonGroup count={4} />}

        {error && (
          <EmptyState
            type="error"
            title="Couldn't load your brief"
            body={error.message}
            actionLabel="Retry"
            onAction={refetch}
          />
        )}

        {!isLoading && !error && !brief && (
          <EmptyState
            type="empty"
            title="No brief yet"
            body="Your daily brief will appear here once your portfolio is set up."
            actionLabel="Add holdings"
            onAction={() => router.push('/(tabs)/portfolio')}
          />
        )}

        {brief && (
          <>
            {/* Hero card */}
            <View style={[styles.heroCard, { backgroundColor: colors.card }]}>
              <View style={styles.heroRow}>
                <View style={styles.heroLeft}>
                  <Text style={[styles.heroLabel, { color: colors.textSecondary }]}>Portfolio today</Text>
                  <DeltaLabel
                    value={`${brief.portfolio_return >= 0 ? '+' : ''}${(brief.portfolio_return * 100).toFixed(2)}%`}
                    size="lg"
                  />
                  <Text style={[styles.riskLabel, { color: colors.textSecondary, marginTop: Spacing.xs }]}>
                    Risk: <Text style={{ color: colors.textPrimary, fontWeight: FontWeight.semibold }}>
                      {brief.risk_level.charAt(0).toUpperCase() + brief.risk_level.slice(1)}
                    </Text>
                  </Text>
                </View>
                <ScoreRing score={brief.health_score} size={88} label="Health" />
              </View>

              <View style={[styles.targetRow, { borderTopColor: colors.border }]}>
                <Text style={[styles.targetLabel, { color: colors.textSecondary }]}>
                  Target probability
                </Text>
                <View style={styles.targetRight}>
                  <Text style={[styles.targetPct, { color: colors.textPrimary }]}>
                    {(brief.target_probability * 100).toFixed(0)}%
                  </Text>
                  <Text style={[styles.targetDelta, { color: pctColor(brief.target_probability_delta) }]}>
                    {brief.target_probability_delta >= 0 ? '+' : ''}{(brief.target_probability_delta * 100).toFixed(0)}% vs yesterday
                  </Text>
                </View>
              </View>
            </View>

            {/* Important */}
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Important</Text>
            {brief.important.length === 0 ? (
              <View style={[styles.calmCard, { backgroundColor: colors.card }]}>
                <Text style={[styles.calmText, { color: colors.textSecondary }]}>
                  Nothing material changed today.
                </Text>
              </View>
            ) : (
              <View style={styles.list}>
                {brief.important.slice(0, 3).map((item) => (
                  <MaterialityRow
                    key={item.id}
                    type={item.change_type as any}
                    title={item.summary}
                    reason={item.detail ?? ''}
                    tickers={item.ticker ? [item.ticker] : []}
                    onPress={() => item.ticker && router.push(`/ticker/${item.ticker}`)}
                  />
                ))}
              </View>
            )}

            {/* Catalysts */}
            {(brief.catalysts?.length ?? 0) > 0 && (
              <>
                <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Catalysts</Text>
                <View style={[styles.catalystCard, { backgroundColor: colors.card }]}>
                  {brief.catalysts.map((cat) => {
                    const color = impactColor(cat.expected_impact);
                    return (
                      <Pressable
                        key={cat.id}
                        style={[styles.catalystRow, { borderBottomColor: colors.border }]}
                        onPress={() => cat.ticker && router.push(`/ticker/${cat.ticker}`)}
                      >
                        <View style={[styles.catIconBg, { backgroundColor: color + '20' }]}>
                          <Ionicons name={CATALYST_ICON[cat.type] as any} size={16} color={color} />
                        </View>
                        <View style={styles.catContent}>
                          <Text style={[styles.catDesc, { color: colors.textPrimary }]} numberOfLines={2}>
                            {cat.description}
                          </Text>
                          <Text style={[styles.catMeta, { color: colors.textMuted }]}>
                            {cat.ticker}
                            {cat.date ? ` · ${new Date(cat.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}` : ''}
                          </Text>
                        </View>
                        <Text style={[styles.catType, { color: colors.textMuted }]}>{cat.type}</Text>
                      </Pressable>
                    );
                  })}
                </View>
              </>
            )}

            {/* Opportunities */}
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Opportunities</Text>
            {brief.opportunities.length === 0 ? (
              <View style={[styles.calmCard, { backgroundColor: colors.card }]}>
                <Text style={[styles.calmText, { color: colors.textSecondary }]}>
                  No high-probability opportunities identified today.
                </Text>
              </View>
            ) : (
              <View style={styles.list}>
                {brief.opportunities.slice(0, 5).map((opp) => (
                  <Pressable
                    key={opp.ticker}
                    style={[styles.oppCard, { backgroundColor: colors.card }]}
                    onPress={() => router.push(`/ticker/${opp.ticker}`)}
                  >
                    <View style={[styles.scoreBadge, { backgroundColor: colors.accent + '22' }]}>
                      <Text style={[styles.scoreText, { color: colors.accent }]}>{opp.score}</Text>
                    </View>
                    <View style={styles.oppContent}>
                      <Text style={[styles.oppTicker, { color: colors.textPrimary }]}>{opp.ticker}</Text>
                      <Text style={[styles.oppThesis, { color: colors.textSecondary }]} numberOfLines={2}>
                        {opp.one_line_thesis}
                      </Text>
                    </View>
                    <ActionPill action={opp.action} size="sm" />
                  </Pressable>
                ))}
              </View>
            )}

            {/* Tomorrow's action plan */}
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Tomorrow</Text>
            <View style={[styles.actionPlanCard, { backgroundColor: colors.card }]}>
              {brief.action_plan.map((item) => (
                <Pressable
                  key={item.ticker}
                  style={styles.actionRow}
                  onPress={() => router.push(`/ticker/${item.ticker}`)}
                >
                  <Text style={[styles.actionTicker, { color: colors.textPrimary }]}>{item.ticker}</Text>
                  <Text style={[styles.actionReason, { color: colors.textSecondary }]} numberOfLines={1}>
                    {item.reason}
                  </Text>
                  <ActionPill action={item.action} size="sm" />
                </Pressable>
              ))}
              {brief.rebalance_required && (
                <View style={[styles.rebalanceBanner, { backgroundColor: colors.amber + '22' }]}>
                  <Text style={[styles.rebalanceText, { color: colors.amber }]}>
                    Rebalance required
                  </Text>
                </View>
              )}
            </View>

            {/* Disclaimer */}
            <Text style={[styles.disclaimer, { color: colors.textMuted }]}>
              For research purposes only. Not investment advice.
            </Text>
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: Spacing.lg, gap: Spacing.lg, paddingBottom: 40 },
  nav: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  navTitle: { fontSize: FontSize.xxl, fontWeight: FontWeight.bold },
  heroCard: { borderRadius: Radius.lg, padding: Spacing.lg, gap: Spacing.md },
  heroRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  heroLeft: { gap: Spacing.xs, flex: 1 },
  heroLabel: { fontSize: FontSize.sm },
  riskLabel: { fontSize: FontSize.sm },
  targetRow: { flexDirection: 'row', justifyContent: 'space-between', paddingTop: Spacing.md, borderTopWidth: 1, marginTop: Spacing.sm },
  targetLabel: { fontSize: FontSize.sm },
  targetRight: { alignItems: 'flex-end', gap: 2 },
  targetPct: { fontSize: FontSize.xl, fontWeight: FontWeight.bold, fontVariant: ['tabular-nums'] },
  targetDelta: { fontSize: FontSize.xs },
  sectionTitle: { fontSize: FontSize.lg, fontWeight: FontWeight.semibold, marginTop: Spacing.sm },
  list: { gap: Spacing.sm },
  calmCard: { padding: Spacing.lg, borderRadius: Radius.md, alignItems: 'center' },
  calmText: { fontSize: FontSize.md },
  catalystCard: { borderRadius: Radius.lg, overflow: 'hidden' },
  catalystRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, padding: Spacing.md, borderBottomWidth: 1 },
  catIconBg: { width: 32, height: 32, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  catContent: { flex: 1, gap: 2 },
  catDesc: { fontSize: FontSize.sm },
  catMeta: { fontSize: FontSize.xs },
  catType: { fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5 },
  oppCard: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, padding: Spacing.md, borderRadius: Radius.md },
  scoreBadge: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
  scoreText: { fontSize: FontSize.sm, fontWeight: FontWeight.bold, fontVariant: ['tabular-nums'] },
  oppContent: { flex: 1, gap: 2 },
  oppTicker: { fontSize: FontSize.md, fontWeight: FontWeight.semibold },
  oppThesis: { fontSize: FontSize.xs },
  actionPlanCard: { borderRadius: Radius.lg, overflow: 'hidden' },
  actionRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, padding: Spacing.md },
  actionTicker: { fontSize: FontSize.sm, fontWeight: FontWeight.bold, width: 44 },
  actionReason: { flex: 1, fontSize: FontSize.xs },
  rebalanceBanner: { padding: Spacing.md, alignItems: 'center' },
  rebalanceText: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold },
  disclaimer: { fontSize: FontSize.xs, textAlign: 'center', marginTop: Spacing.md, fontStyle: 'italic' },
});
