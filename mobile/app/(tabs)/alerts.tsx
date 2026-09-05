import React, { useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, Pressable,
  useColorScheme, RefreshControl,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuthStore } from '@/stores/authStore';
import { useAlerts, useMarkAlertRead } from '@/hooks/useAlerts';
import { MaterialityRow } from '@/components/ui/MaterialityRow';
import { SkeletonGroup } from '@/components/ui/SkeletonCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing } from '@/constants/Theme';
import type { Alert, AlertType } from '@/lib/types';

const FILTER_OPTIONS: Array<{ label: string; value: AlertType | 'all' }> = [
  { label: 'All', value: 'all' },
  { label: 'Portfolio', value: 'risk' },
  { label: 'Watchlist', value: 'catalyst' },
  { label: 'Risk', value: 'news' },
];

function groupByDay(alerts: Alert[]): Array<{ date: string; items: Alert[] }> {
  const map = new Map<string, Alert[]>();
  for (const a of alerts) {
    const day = a.created_at.slice(0, 10);
    if (!map.has(day)) map.set(day, []);
    map.get(day)!.push(a);
  }
  return Array.from(map.entries()).map(([date, items]) => ({ date, items }));
}

function formatDate(isoDate: string): string {
  const d = new Date(isoDate);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = today.getTime() - new Date(isoDate).setHours(0, 0, 0, 0);
  if (diff === 0) return 'Today';
  if (diff === 86400000) return 'Yesterday';
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function AlertsScreen() {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const router = useRouter();

  const { user } = useAuthStore();
  const { data: alerts, isLoading, refetch, isFetching } = useAlerts(user?.id ?? null);
  const { mutate: markRead } = useMarkAlertRead();

  const [filter, setFilter] = useState<AlertType | 'all'>('all');

  const filtered = (alerts ?? []).filter((a) => filter === 'all' || a.type === filter);
  const groups = groupByDay(filtered);

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Alerts</Text>
        <View style={styles.filterRow}>
          {FILTER_OPTIONS.map((opt) => (
            <Pressable
              key={opt.value}
              style={[
                styles.filterChip,
                {
                  backgroundColor: filter === opt.value ? colors.accent : 'transparent',
                  borderColor: filter === opt.value ? colors.accent : colors.border,
                },
              ]}
              onPress={() => setFilter(opt.value)}
            >
              <Text style={[styles.filterText, { color: filter === opt.value ? '#fff' : colors.textSecondary }]}>
                {opt.label}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      {isLoading && <SkeletonGroup count={4} />}

      {!isLoading && filtered.length === 0 && (
        <EmptyState
          type="empty"
          title="No alerts"
          body="Material events for your portfolio and watchlist will appear here."
        />
      )}

      <FlatList
        data={groups}
        keyExtractor={(g) => g.date}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={isFetching} onRefresh={refetch} tintColor={colors.accent} />}
        renderItem={({ item: group }) => (
          <View style={styles.group}>
            <Text style={[styles.groupDate, { color: colors.textMuted }]}>{formatDate(group.date)}</Text>
            {group.items.map((alert) => (
              <Pressable
                key={alert.id}
                style={{ opacity: alert.read_at ? 0.6 : 1 }}
                onPress={() => {
                  markRead(alert.id);
                  if (alert.tickers.length > 0) router.push(`/ticker/${alert.tickers[0]}`);
                }}
              >
                <MaterialityRow
                  type={alert.type}
                  title={alert.title}
                  reason={alert.body}
                  tickers={alert.tickers}
                />
              </Pressable>
            ))}
          </View>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { padding: Spacing.lg, gap: Spacing.md },
  title: { fontSize: FontSize.xxl, fontWeight: FontWeight.bold },
  filterRow: { flexDirection: 'row', gap: Spacing.sm, flexWrap: 'wrap' },
  filterChip: { paddingHorizontal: Spacing.md, paddingVertical: Spacing.xs, borderRadius: 999, borderWidth: 1 },
  filterText: { fontSize: FontSize.xs, fontWeight: FontWeight.semibold },
  list: { padding: Spacing.lg, gap: Spacing.xl, paddingBottom: 40 },
  group: { gap: Spacing.sm },
  groupDate: { fontSize: FontSize.xs, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: Spacing.xs },
});
