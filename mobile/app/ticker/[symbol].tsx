import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable,
  useColorScheme, ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import {
  useTickerAnalysis, useTickerQuote, useRelationships,
  useWatchlistStatus, useToggleWatchlist,
} from '@/hooks/useTicker';
import { usePortfolioStore } from '@/stores/portfolioStore';
import { useAuthStore } from '@/stores/authStore';
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
import type { Fundamental, TechnicalSnapshot, ForecastYear } from '@/lib/types';

export default function TickerScreen() {
  const { symbol } = useLocalSearchParams<{ symbol: string }>();
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const router = useRouter();

  const { activePortfolioId } = usePortfolioStore();
  const { user } = useAuthStore();

  const { data: quote } = useTickerQuote(symbol ?? '');
  const { data: relationships } = useRelationships(symbol ?? '');
  const { data: watchStatus } = useWatchlistStatus(symbol ?? '', user?.id);
  const { mutate: toggleWatchlist, isPending: togglingWatch } = useToggleWatchlist(symbol ?? '', user?.id);

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
          <Pressable
            hitSlop={8}
            accessibilityLabel={watchStatus?.isWatchlisted ? 'Remove from watchlist' : 'Add to watchlist'}
            onPress={() => watchStatus && toggleWatchlist(watchStatus)}
            disabled={togglingWatch || !user}
          >
            <Ionicons
              name={watchStatus?.isWatchlisted ? 'star' : 'star-outline'}
              size={22}
              color={watchStatus?.isWatchlisted ? colors.amber : colors.textSecondary}
            />
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
                  {analysis.valuation_range.assumptions_version ? ` · v${analysis.valuation_range.assumptions_version}` : ''}
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

        {/* Technicals */}
        {analysis?.technical_snapshot && (
          <CollapsibleSection
            title="Technicals"
            sectionKey="technicals"
            expanded={expandedSections.has('technicals')}
            onToggle={toggleSection}
            colors={colors}
            badge={<ForecastPill />}
          >
            <TechnicalsGrid snapshot={analysis.technical_snapshot} colors={colors} />
          </CollapsibleSection>
        )}

        {/* Forecast model */}
        {analysis?.forecast_model && analysis.forecast_model.length > 0 && (
          <CollapsibleSection
            title="Forecast model"
            sectionKey="forecast"
            expanded={expandedSections.has('forecast')}
            onToggle={toggleSection}
            colors={colors}
            badge={<ForecastPill />}
          >
            <ForecastTable model={analysis.forecast_model} colors={colors} />
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
        {relationships?.data?.data && (relationships.data.data as any[]).length > 0 && (
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

        {/* Full report */}
        {analysis?.full_report_markdown && (
          <CollapsibleSection
            title="Full report"
            sectionKey="full_report"
            expanded={expandedSections.has('full_report')}
            onToggle={toggleSection}
            colors={colors}
          >
            <Text style={[styles.reportText, { color: colors.textSecondary }]}>
              {analysis.full_report_markdown}
            </Text>
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

// ─── Collapsible section ──────────────────────────────────────────────────────

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

// ─── Earnings table ───────────────────────────────────────────────────────────

function EarningsTable({ earnings, colors }: { earnings: Fundamental; colors: typeof Colors.dark }) {
  function BeatMiss({ actual, expected }: { actual: string | null; expected: string | null }) {
    if (!actual || !expected) return null;
    const a = parseFloat(actual);
    const e = parseFloat(expected);
    if (isNaN(a) || isNaN(e) || e === 0) return null;
    const beat = a >= e;
    const delta = ((a - e) / Math.abs(e) * 100).toFixed(1);
    return (
      <View style={[styles.beatBadge, { backgroundColor: beat ? colors.green + '20' : colors.red + '20' }]}>
        <Text style={[styles.beatText, { color: beat ? colors.green : colors.red }]}>
          {beat ? '+' : ''}{delta}%
        </Text>
      </View>
    );
  }

  const rows = [
    { label: 'Revenue', actual: earnings.revenue, expected: null },
    { label: 'EPS', actual: earnings.eps, expected: earnings.eps_expected },
    { label: 'Free cash flow', actual: earnings.fcf, expected: null },
    {
      label: 'Gross margin',
      actual: earnings.gross_margin != null ? `${(earnings.gross_margin * 100).toFixed(1)}%` : null,
      expected: null,
    },
    {
      label: 'Op. margin',
      actual: earnings.operating_margin != null ? `${(earnings.operating_margin * 100).toFixed(1)}%` : null,
      expected: null,
    },
  ].filter((r) => r.actual != null);

  return (
    <View style={styles.earningsTable}>
      {rows.map((row) => (
        <View key={row.label} style={[styles.earningsRow, { borderBottomColor: colors.border }]}>
          <Text style={[styles.earningsLabel, { color: colors.textSecondary }]}>{row.label}</Text>
          <Text style={[styles.earningsValue, { color: colors.textPrimary }]}>{row.actual}</Text>
          {row.expected && (
            <Text style={[styles.earningsExpected, { color: colors.textMuted }]}>exp. {row.expected}</Text>
          )}
          <BeatMiss actual={row.actual} expected={row.expected} />
        </View>
      ))}

      {(earnings.guidance_revenue || earnings.guidance_eps) && (
        <View style={[styles.guidanceBlock, { borderTopColor: colors.border }]}>
          <Text style={[styles.guidanceHeader, { color: colors.textMuted }]}>GUIDANCE</Text>
          {earnings.guidance_revenue && (
            <View style={[styles.earningsRow, { borderBottomColor: colors.border }]}>
              <Text style={[styles.earningsLabel, { color: colors.textSecondary }]}>Revenue</Text>
              <Text style={[styles.earningsValue, { color: colors.textPrimary }]}>{earnings.guidance_revenue}</Text>
            </View>
          )}
          {earnings.guidance_eps && (
            <View style={[styles.earningsRow, { borderBottomColor: 'transparent' }]}>
              <Text style={[styles.earningsLabel, { color: colors.textSecondary }]}>EPS</Text>
              <Text style={[styles.earningsValue, { color: colors.textPrimary }]}>{earnings.guidance_eps}</Text>
            </View>
          )}
        </View>
      )}
    </View>
  );
}

// ─── Technicals grid ──────────────────────────────────────────────────────────

function TechnicalsGrid({ snapshot, colors }: { snapshot: TechnicalSnapshot; colors: typeof Colors.dark }) {
  const rsiColor =
    snapshot.rsi_14 == null ? colors.textPrimary
    : snapshot.rsi_14 > 70 ? colors.red
    : snapshot.rsi_14 < 30 ? colors.green
    : colors.textPrimary;

  const rows: Array<{ label: string; value: string; note?: string; noteColor?: string }> = [
    snapshot.rsi_14 != null && {
      label: 'RSI (14)',
      value: snapshot.rsi_14.toFixed(1),
      note: snapshot.rsi_14 > 70 ? 'Overbought' : snapshot.rsi_14 < 30 ? 'Oversold' : '',
      noteColor: rsiColor,
    },
    snapshot.macd_line != null && { label: 'MACD', value: snapshot.macd_line.toFixed(3) },
    snapshot.macd_signal != null && { label: 'Signal', value: snapshot.macd_signal.toFixed(3) },
    snapshot.sma_20 != null && { label: 'SMA 20', value: `$${snapshot.sma_20.toFixed(2)}` },
    snapshot.sma_50 != null && { label: 'SMA 50', value: `$${snapshot.sma_50.toFixed(2)}` },
    snapshot.sma_200 != null && { label: 'SMA 200', value: `$${snapshot.sma_200.toFixed(2)}` },
    snapshot.atr_14 != null && { label: 'ATR (14)', value: snapshot.atr_14.toFixed(2) },
    snapshot.vwap != null && { label: 'VWAP', value: `$${snapshot.vwap.toFixed(2)}` },
    snapshot.relative_volume != null && { label: 'Rel. Volume', value: `${snapshot.relative_volume.toFixed(2)}×` },
  ].filter(Boolean) as Array<{ label: string; value: string; note?: string; noteColor?: string }>;

  return (
    <View>
      {rows.map((row, i) => (
        <View
          key={row.label}
          style={[styles.techRow, { borderBottomColor: colors.border, borderBottomWidth: i < rows.length - 1 ? 1 : 0 }]}
        >
          <Text style={[styles.techLabel, { color: colors.textSecondary }]}>{row.label}</Text>
          <Text style={[styles.techValue, { color: colors.textPrimary }]}>{row.value}</Text>
          {!!row.note && (
            <Text style={[styles.techNote, { color: row.noteColor ?? colors.textMuted }]}>{row.note}</Text>
          )}
        </View>
      ))}
    </View>
  );
}

// ─── Forecast model table ─────────────────────────────────────────────────────

function ForecastTable({ model, colors }: { model: ForecastYear[]; colors: typeof Colors.dark }) {
  type MetricDef = { key: keyof ForecastYear; label: string; fmt?: (v: any) => string };
  const allMetrics: MetricDef[] = [
    { key: 'revenue', label: 'Revenue' },
    { key: 'revenue_growth', label: 'Rev. Growth', fmt: (v) => `${(v * 100).toFixed(1)}%` },
    { key: 'gross_margin', label: 'Gross Margin', fmt: (v) => `${(v * 100).toFixed(1)}%` },
    { key: 'eps', label: 'EPS' },
    { key: 'fcf', label: 'FCF' },
  ];

  const visibleMetrics = allMetrics.filter((m) => model.some((y) => y[m.key] != null));

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
      <View>
        <View style={[styles.forecastRow, { borderBottomColor: colors.border }]}>
          <Text style={[styles.forecastMetricLabel, { color: colors.textMuted }]} />
          {model.map((y) => (
            <Text key={y.fiscal_year} style={[styles.forecastYearLabel, { color: colors.textMuted }]}>
              {y.fiscal_year}
            </Text>
          ))}
        </View>
        {visibleMetrics.map((metric) => (
          <View key={metric.key} style={[styles.forecastRow, { borderBottomColor: colors.border }]}>
            <Text style={[styles.forecastMetricLabel, { color: colors.textSecondary }]}>{metric.label}</Text>
            {model.map((y) => {
              const raw = y[metric.key];
              const display = raw == null ? '—' : metric.fmt ? metric.fmt(raw) : String(raw);
              return (
                <Text key={y.fiscal_year} style={[styles.forecastValue, { color: colors.textPrimary }]}>
                  {display}
                </Text>
              );
            })}
          </View>
        ))}
      </View>
    </ScrollView>
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
  methodLabel: { fontSize: FontSize.xs, marginTop: Spacing.sm },
  section: { borderRadius: Radius.lg, overflow: 'hidden' },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: Spacing.lg },
  sectionTitleRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  sectionTitle: { fontSize: FontSize.md, fontWeight: FontWeight.semibold },
  sectionBody: { padding: Spacing.lg, paddingTop: 0, gap: Spacing.sm },
  // Earnings
  earningsTable: {},
  earningsRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: Spacing.md, borderBottomWidth: 1, gap: Spacing.sm },
  earningsLabel: { flex: 1, fontSize: FontSize.sm },
  earningsValue: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold, fontVariant: ['tabular-nums'] },
  earningsExpected: { fontSize: FontSize.xs },
  beatBadge: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  beatText: { fontSize: 10, fontWeight: FontWeight.semibold, fontVariant: ['tabular-nums'] },
  guidanceBlock: { borderTopWidth: 1, marginTop: Spacing.sm, paddingTop: Spacing.sm },
  guidanceHeader: { fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.8, paddingVertical: Spacing.xs },
  // Technicals
  techRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: Spacing.sm, gap: Spacing.sm },
  techLabel: { flex: 1, fontSize: FontSize.sm },
  techValue: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold, fontVariant: ['tabular-nums'] },
  techNote: { fontSize: FontSize.xs, minWidth: 64, textAlign: 'right' },
  // Forecast
  forecastRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: Spacing.sm, borderBottomWidth: 1, gap: Spacing.md },
  forecastMetricLabel: { width: 100, fontSize: FontSize.xs },
  forecastYearLabel: { width: 72, fontSize: FontSize.xs, fontWeight: FontWeight.semibold, textAlign: 'right' },
  forecastValue: { width: 72, fontSize: FontSize.sm, fontVariant: ['tabular-nums'], textAlign: 'right' },
  // Relationships
  list: { gap: Spacing.sm },
  relRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: Spacing.sm, borderBottomWidth: 1 },
  relType: { width: 90, fontSize: FontSize.xs },
  relName: { flex: 1, fontSize: FontSize.sm },
  relWeight: { fontSize: FontSize.xs, fontVariant: ['tabular-nums'] },
  // Full report
  reportText: { fontSize: FontSize.xs, lineHeight: 20, fontFamily: 'Courier' },
  // Portfolio fit
  fitCard: { borderRadius: Radius.lg, padding: Spacing.lg, gap: Spacing.sm },
  fitLabel: { fontSize: FontSize.xs, textTransform: 'uppercase', letterSpacing: 0.8 },
  fitText: { fontSize: FontSize.sm, lineHeight: 22 },
  // Compare
  compareBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.sm, padding: Spacing.lg, borderRadius: Radius.lg, borderWidth: 1 },
  compareBtnText: { fontSize: FontSize.sm },
  disclaimer: { textAlign: 'center', fontSize: FontSize.xs, fontStyle: 'italic' },
});
