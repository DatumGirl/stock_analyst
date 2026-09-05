import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable,
  useColorScheme, ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTickerAnalysis, useTickerQuote, useRelationships } from '@/hooks/useTicker';
import { usePortfolioStore } from '@/stores/portfolioStore';
import { SignalChips } from '@/components/ui/SignalChips';
import { RangeBar } from '@/components/ui/RangeBar';
import { DeltaLabel } from '@/components/ui/DeltaLabel';
import { FreshnessStamp } from '@/components/ui/FreshnessStamp';
import { ForecastPill } from '@/components/ui/ForecastPill';
import { ActionPill } from '@/components/ui/ActionPill';
import { MaterialityRow } from '@/components/ui/MaterialityRow';
import { SkeletonGroup } from '@/components/ui/SkeletonCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing, Radius } from '@/constants/Theme';

export default function TickerScreen() {
  const { symbol } = useLocalSearchParams<{ symbol: string }>();
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const router = useRouter();

  const { activePortfolioId } = usePortfolioStore();
  const { data: quote } = useTickerQuote(symbol ?? '');
  const { data: relationships } = useRelationships(symbol ?? '');

  const {
    mutate: analyze,
    data: analysisEnvelope,
    isPending: analyzing,
    error: analysisError,
  } = useTickerAnalysis(symbol ?? '', activePortfolioId ?? undefined);

  const analysis = analysisEnvelope?.data;

  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['earnings', 'whats_driving']),
  );

  function toggleSection(key: string) {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  if (!symbol) {
    return <EmptyState type="error" title="No ticker specified" />;
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top', 'bottom']}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* Nav */}
        <View style={styles.nav}>
          <Pressable onPress={() => router.back()} hitSlop={8} accessibilityLabel="Back">
            <Ionicons name="chevron-back" size={24} color={colors.textPrimary} />
          </Pressable>
          <Text style={[styles.symbol, { color: colors.textPrimary }]}>{symbol}</Text>
          <Pressable hitSlop={8} accessibilityLabel="Add to watchlist">
            <Ionicons name="star-outline" size={22} color={colors.textSecondary} />
          </Pressable>
        </View>

        {/* Price header */}
        <View style={[styles.priceCard, { backgroundColor: colors.card }]}>
          {quote ? (
            <>
              <DeltaLabel
                value={`$${parseFloat(quote.price).toFixed(2)}`}
                changePct={quote.change_pct}
                size="lg"
              />
              <FreshnessStamp asOf={quote.as_of} refreshIntervalMinutes={5} />
            </>
          ) : (
            <Text style={[styles.noPriceText, { color: colors.textMuted }]}>Price loading…</Text>
          )}
        </View>

        {/* Verdict card */}
        {analysis && (
          <View style={[styles.verdictCard, { backgroundColor: colors.card }]}>
            <View style={styles.verdictHeader}>
              <Text style={[styles.verdictText, { color: colors.textPrimary }]}>{analysis.verdict}</Text>
              <ActionPill action={analysis.action} />
            </View>
            <SignalChips signals={analysis.signals} />
            {analysis.model_disagreements.length > 0 && (
              <View style={[styles.disagreementRow, { backgroundColor: colors.amber + '15' }]}>
                <Ionicons name="alert-outline" size={14} color={colors.amber} />
                <Text style={[styles.disagreementText, { color: colors.amber }]}>
                  {analysis.model_disagreements.join(' · ')}
                </Text>
              </View>
            )}
          </View>
        )}

        {/* Analyze button */}
        {!analysis && !analyzing && (
          <Pressable
            style={[styles.analyzeBtn, { backgroundColor: colors.accent }]}
            onPress={() => analyze()}
          >
            <Ionicons name="analytics-outline" size={18} color="#fff" />
            <Text style={styles.analyzeBtnText}>Analyze now</Text>
          </Pressable>
        )}

        {analyzing && (
          <View style={[styles.analyzingCard, { backgroundColor: colors.card }]}>
            <ActivityIndicator color={colors.accent} />
            <Text style={[styles.analyzingText, { color: colors.textSecondary }]}>
              Gathering data, running valuation… (30–60 s)
            </Text>
          </View>
        )}

        {analysisError && (
          <EmptyState
            type="error"
            title="Analysis failed"
            body={analysisError.message}
            actionLabel="Retry"
            onAction={() => analyze()}
          />
        )}

        {/* Fair value */}
        {analysis && (
          <CollapsibleSection
            title="Fair value"
            sectionKey="valuation"
            expanded={expandedSections.has('valuation')}
            onToggle={toggleSection}
            colors={colors}
            badge={<ForecastPill />}
          >
            {analysis.valuation_range ? (
              <>
                <RangeBar
                  low={parseFloat(analysis.valuation_range.low)}
                  base={parseFloat(analysis.valuation_range.base)}
                  high={parseFloat(analysis.valuation_range.high)}
                  bear={parseFloat(analysis.valuation_range.bear)}
                  bull={parseFloat(analysis.valuation_range.bull)}
                  current={quote ? parseFloat(quote.price) : undefined}
                />
                <Text style={[styles.methodLabel, { color: colors.textMuted }]}>
                  Method: {analysis.valuation_range.method.toUpperCase()} · {analysis.valuation_range.source}
                </Text>
              </>
            ) : (
              <Text style={[styles.methodLabel, { color: colors.textMuted }]}>
                Insufficient fundamental data to compute a valuation range for this ticker.
              </Text>
            )}
          </CollapsibleSection>
        )}

        {/* Earnings */}
        {analysis?.earnings && (
          <CollapsibleSection
            title="Earnings"
            sectionKey="earnings"
            expanded={expandedSections.has('earnings')}
            onToggle={toggleSection}
            colors={colors}
          >
            <EarningsTable earnings={analysis.earnings} colors={colors} />
          </CollapsibleSection>
        )}

        {/* What's driving it */}
        {analysis && (analysis.what_is_driving?.length ?? 0) > 0 && (
          <CollapsibleSection
            title="What's driving it"
            sectionKey="whats_driving"
            expanded={expandedSections.has('whats_driving')}
            onToggle={toggleSection}
            colors={colors}
          >
            <View style={styles.list}>
              {(analysis.what_is_driving ?? []).map((event) => (
                <MaterialityRow
                  key={event.id}
                  type="news"
                  title={event.headline}
                  reason={`${event.sentiment} · materiality ${(event.materiality_score * 100).toFixed(0)}%`}
                  tickers={event.tickers}
                />
              ))}
            </View>
          </CollapsibleSection>
        )}

        {/* Relationships (graph) */}
        {relationships?.data?.data && relationships.data.data.length > 0 && (
          <CollapsibleSection
            title="Relationships"
            sectionKey="relationships"
            expanded={expandedSections.has('relationships')}
            onToggle={toggleSection}
            colors={colors}
          >
            {(relationships.data.data as any[]).slice(0, 8).map((rel: any, i: number) => (
              <View key={i} style={[styles.relRow, { borderBottomColor: colors.border }]}>
                <Text style={[styles.relType, { color: colors.textMuted }]}>{rel.rel_type}</Text>
                <Text style={[styles.relName, { color: colors.textPrimary }]}>{rel.name ?? rel.key}</Text>
                {rel.weight != null && (
                  <Text style={[styles.relWeight, { color: colors.textSecondary }]}>
                    {(rel.weight * 100).toFixed(0)}%
                  </Text>
                )}
              </View>
            ))}
          </CollapsibleSection>
        )}

        {/* Portfolio fit */}
        {analysis?.portfolio_fit && (
          <View style={[styles.fitCard, { backgroundColor: colors.card }]}>
            <Text style={[styles.fitLabel, { color: colors.textMuted }]}>Portfolio fit</Text>
            <Text style={[styles.fitText, { color: colors.textPrimary }]}>{analysis.portfolio_fit}</Text>
          </View>
        )}

        {/* Compare button */}
        <Pressable
          style={[styles.compareBtn, { borderColor: colors.border }]}
          onPress={() => router.push({ pathname: '/compare', params: { initial: symbol } })}
        >
          <Ionicons name="git-compare-outline" size={16} color={colors.textSecondary} />
          <Text style={[styles.compareBtnText, { color: colors.textSecondary }]}>Compare</Text>
        </Pressable>

        <Text style={[styles.disclaimer, { color: colors.textMuted }]}>
          Not investment advice. All analysis is for research only.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function CollapsibleSection({
  title, sectionKey, expanded, onToggle, children, badge, colors,
}: {
  title: string;
  sectionKey: string;
  expanded: boolean;
  onToggle: (k: string) => void;
  children: React.ReactNode;
  badge?: React.ReactNode;
  colors: typeof Colors.dark;
}) {
  return (
    <View style={[styles.section, { backgroundColor: colors.card }]}>
      <Pressable style={styles.sectionHeader} onPress={() => onToggle(sectionKey)}>
        <View style={styles.sectionTitleRow}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>{title}</Text>
          {badge}
        </View>
        <Ionicons
          name={expanded ? 'chevron-up' : 'chevron-down'}
          size={18}
          color={colors.textMuted}
        />
      </Pressable>
      {expanded && <View style={styles.sectionBody}>{children}</View>}
    </View>
  );
}

function EarningsTable({ earnings, colors }: { earnings: NonNullable<any>; colors: typeof Colors.dark }) {
  const rows = [
    { label: 'Revenue', actual: earnings.revenue, expected: null },
    { label: 'EPS', actual: earnings.eps, expected: earnings.eps_expected },
    { label: 'Gross margin', actual: earnings.gross_margin != null ? `${(earnings.gross_margin * 100).toFixed(1)}%` : null, expected: null },
    { label: 'Operating margin', actual: earnings.operating_margin != null ? `${(earnings.operating_margin * 100).toFixed(1)}%` : null, expected: null },
  ];

  return (
    <View style={styles.earningsTable}>
      {rows.filter((r) => r.actual != null).map((row) => (
        <View key={row.label} style={[styles.earningsRow, { borderBottomColor: colors.border }]}>
          <Text style={[styles.earningsLabel, { color: colors.textSecondary }]}>{row.label}</Text>
          <Text style={[styles.earningsValue, { color: colors.textPrimary }]}>{row.actual}</Text>
          {row.expected && (
            <Text style={[styles.earningsExpected, { color: colors.textMuted }]}>exp. {row.expected}</Text>
          )}
        </View>
      ))}
      {earnings.guidance_revenue && (
        <View style={[styles.earningsRow, { borderBottomColor: colors.border }]}>
          <Text style={[styles.earningsLabel, { color: colors.textSecondary }]}>Guidance revenue</Text>
          <Text style={[styles.earningsValue, { color: colors.textPrimary }]}>{earnings.guidance_revenue}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: 40 },
  nav: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  symbol: { fontSize: FontSize.xl, fontWeight: FontWeight.bold },
  priceCard: { borderRadius: Radius.lg, padding: Spacing.lg, gap: Spacing.xs },
  noPriceText: { fontSize: FontSize.md },
  verdictCard: { borderRadius: Radius.lg, padding: Spacing.lg, gap: Spacing.md },
  verdictHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: Spacing.md },
  verdictText: { flex: 1, fontSize: FontSize.md, lineHeight: 22 },
  disagreementRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.xs, padding: Spacing.sm, borderRadius: Radius.sm },
  disagreementText: { fontSize: FontSize.xs, flex: 1 },
  analyzeBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.sm, padding: Spacing.lg, borderRadius: Radius.lg },
  analyzeBtnText: { color: '#fff', fontSize: FontSize.md, fontWeight: FontWeight.semibold },
  analyzingCard: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, padding: Spacing.lg, borderRadius: Radius.lg },
  analyzingText: { fontSize: FontSize.sm },
  section: { borderRadius: Radius.lg, overflow: 'hidden' },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: Spacing.lg },
  sectionTitleRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  sectionTitle: { fontSize: FontSize.md, fontWeight: FontWeight.semibold },
  sectionBody: { padding: Spacing.lg, paddingTop: 0, gap: Spacing.sm },
  methodLabel: { fontSize: FontSize.xs, marginTop: Spacing.sm },
  earningsTable: { gap: 0 },
  earningsRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: Spacing.md, borderBottomWidth: 1 },
  earningsLabel: { flex: 1, fontSize: FontSize.sm },
  earningsValue: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold, fontVariant: ['tabular-nums'] },
  earningsExpected: { fontSize: FontSize.xs, marginLeft: Spacing.sm },
  list: { gap: Spacing.sm },
  relRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: Spacing.sm, borderBottomWidth: 1 },
  relType: { width: 90, fontSize: FontSize.xs },
  relName: { flex: 1, fontSize: FontSize.sm },
  relWeight: { fontSize: FontSize.xs, fontVariant: ['tabular-nums'] },
  fitCard: { borderRadius: Radius.lg, padding: Spacing.lg, gap: Spacing.sm },
  fitLabel: { fontSize: FontSize.xs, textTransform: 'uppercase', letterSpacing: 0.8 },
  fitText: { fontSize: FontSize.sm, lineHeight: 22 },
  compareBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.sm, padding: Spacing.lg, borderRadius: Radius.lg, borderWidth: 1 },
  compareBtnText: { fontSize: FontSize.sm },
  disclaimer: { textAlign: 'center', fontSize: FontSize.xs, fontStyle: 'italic' },
});
