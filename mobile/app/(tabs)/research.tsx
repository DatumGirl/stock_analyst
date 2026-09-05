import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, FlatList,
  useColorScheme, Pressable, ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useTickerSearch } from '@/hooks/useTicker';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing, Radius } from '@/constants/Theme';
import type { Ticker } from '@/lib/types';

const RECENT_TICKERS = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN'];

export default function ResearchScreen() {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const router = useRouter();

  const [query, setQuery] = useState('');
  const { data: results, isLoading } = useTickerSearch(query);

  function navigateTicker(symbol: string) {
    router.push(`/ticker/${symbol}`);
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Research</Text>

        {/* Search bar */}
        <View style={[styles.searchBar, { backgroundColor: colors.card, borderColor: colors.border }]}>
          <Ionicons name="search" size={18} color={colors.textMuted} />
          <TextInput
            style={[styles.searchInput, { color: colors.textPrimary }]}
            placeholder="Search ticker or company…"
            placeholderTextColor={colors.textMuted}
            autoCapitalize="characters"
            autoCorrect={false}
            value={query}
            onChangeText={setQuery}
            returnKeyType="search"
            onSubmitEditing={() => query && navigateTicker(query.toUpperCase())}
          />
          {query.length > 0 && (
            <Pressable onPress={() => setQuery('')} hitSlop={8}>
              <Ionicons name="close-circle" size={18} color={colors.textMuted} />
            </Pressable>
          )}
        </View>
      </View>

      {isLoading && (
        <ActivityIndicator style={styles.loader} color={colors.accent} />
      )}

      {query.length > 0 && results && results.length > 0 && (
        <FlatList
          data={results}
          keyExtractor={(item) => item.symbol}
          contentContainerStyle={styles.resultList}
          renderItem={({ item }) => <TickerRow ticker={item} onPress={() => navigateTicker(item.symbol)} colors={colors} />}
        />
      )}

      {query.length === 0 && (
        <View style={styles.recentSection}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>Recent</Text>
          <View style={styles.recentChips}>
            {RECENT_TICKERS.map((t) => (
              <Pressable
                key={t}
                style={[styles.recentChip, { backgroundColor: colors.card, borderColor: colors.border }]}
                onPress={() => navigateTicker(t)}
              >
                <Text style={[styles.recentChipText, { color: colors.textPrimary }]}>{t}</Text>
              </Pressable>
            ))}
          </View>

          <Text style={[styles.sectionLabel, { color: colors.textMuted, marginTop: Spacing.xl }]}>
            Commands
          </Text>
          {[
            { label: 'Analyze a ticker', desc: 'Deep analysis with valuation, earnings, and sentiment', icon: 'analytics-outline' as const },
            { label: 'Compare tickers', desc: 'Side-by-side comparison of up to 4 companies', icon: 'git-compare-outline' as const },
          ].map((cmd) => (
            <Pressable
              key={cmd.label}
              style={[styles.cmdCard, { backgroundColor: colors.card }]}
              onPress={() => cmd.label.includes('Compare') && router.push('/compare')}
            >
              <Ionicons name={cmd.icon} size={20} color={colors.accent} />
              <View style={styles.cmdText}>
                <Text style={[styles.cmdLabel, { color: colors.textPrimary }]}>{cmd.label}</Text>
                <Text style={[styles.cmdDesc, { color: colors.textSecondary }]}>{cmd.desc}</Text>
              </View>
            </Pressable>
          ))}
        </View>
      )}
    </SafeAreaView>
  );
}

function TickerRow({ ticker, onPress, colors }: { ticker: Ticker; onPress: () => void; colors: typeof Colors.dark }) {
  return (
    <Pressable style={[styles.tickerRow, { borderBottomColor: colors.border }]} onPress={onPress}>
      <View style={[styles.symbolBadge, { backgroundColor: colors.accent + '22' }]}>
        <Text style={[styles.symbol, { color: colors.accent }]}>{ticker.symbol}</Text>
      </View>
      <View style={styles.tickerInfo}>
        <Text style={[styles.tickerName, { color: colors.textPrimary }]} numberOfLines={1}>{ticker.name}</Text>
        <Text style={[styles.tickerMeta, { color: colors.textMuted }]}>
          {[ticker.sector, ticker.exchange].filter(Boolean).join(' · ')}
        </Text>
      </View>
      <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { padding: Spacing.lg, gap: Spacing.md },
  title: { fontSize: FontSize.xxl, fontWeight: FontWeight.bold },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    padding: Spacing.md,
    borderRadius: Radius.md,
    borderWidth: 1,
  },
  searchInput: { flex: 1, fontSize: FontSize.md, height: 28 },
  loader: { marginTop: Spacing.xl },
  resultList: { padding: Spacing.lg, gap: 0 },
  tickerRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, paddingVertical: Spacing.md, borderBottomWidth: 1 },
  symbolBadge: { width: 52, height: 36, borderRadius: Radius.sm, alignItems: 'center', justifyContent: 'center' },
  symbol: { fontSize: FontSize.sm, fontWeight: FontWeight.bold },
  tickerInfo: { flex: 1 },
  tickerName: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold },
  tickerMeta: { fontSize: FontSize.xs, marginTop: 2 },
  recentSection: { padding: Spacing.lg, gap: Spacing.md },
  sectionLabel: { fontSize: FontSize.xs, textTransform: 'uppercase', letterSpacing: 0.8 },
  recentChips: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm },
  recentChip: { paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm, borderRadius: Radius.full, borderWidth: 1 },
  recentChipText: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold },
  cmdCard: { flexDirection: 'row', alignItems: 'center', gap: Spacing.lg, padding: Spacing.lg, borderRadius: Radius.md },
  cmdText: { flex: 1, gap: 2 },
  cmdLabel: { fontSize: FontSize.md, fontWeight: FontWeight.semibold },
  cmdDesc: { fontSize: FontSize.sm },
});
