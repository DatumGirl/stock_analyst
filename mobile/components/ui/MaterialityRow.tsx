import React from 'react';
import { View, Text, StyleSheet, Pressable, useColorScheme } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '@/constants/Colors';
import { FontSize, Spacing, Radius, FontWeight } from '@/constants/Theme';
import type { AlertType } from '@/lib/types';

interface Props {
  type: AlertType;
  title: string;
  reason: string;
  tickers?: string[];
  onPress?: () => void;
}

const TYPE_ICON: Record<AlertType, { name: keyof typeof Ionicons.glyphMap; color: (c: typeof Colors.dark) => string }> = {
  risk: { name: 'warning-outline', color: (c) => c.amber },
  catalyst: { name: 'calendar-outline', color: (c) => c.accent },
  news: { name: 'newspaper-outline', color: (c) => c.textSecondary },
  thesis: { name: 'document-text-outline', color: (c) => c.forecast },
  price: { name: 'trending-up-outline', color: (c) => c.green },
};

export function MaterialityRow({ type, title, reason, tickers, onPress }: Props) {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const icon = TYPE_ICON[type];

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.row,
        { backgroundColor: colors.card, opacity: pressed ? 0.7 : 1 },
      ]}
      accessibilityRole="button"
    >
      <View style={[styles.iconWrap, { backgroundColor: icon.color(colors) + '22' }]}>
        <Ionicons name={icon.name} size={18} color={icon.color(colors)} />
      </View>

      <View style={styles.content}>
        <Text style={[styles.title, { color: colors.textPrimary }]} numberOfLines={2}>
          {title}
        </Text>
        <Text style={[styles.reason, { color: colors.textSecondary }]} numberOfLines={1}>
          {reason}
        </Text>
        {tickers && tickers.length > 0 && (
          <View style={styles.tickers}>
            {tickers.map((t) => (
              <View key={t} style={[styles.tickerPill, { backgroundColor: colors.border }]}>
                <Text style={[styles.tickerText, { color: colors.textPrimary }]}>{t}</Text>
              </View>
            ))}
          </View>
        )}
      </View>

      <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    padding: Spacing.md,
    borderRadius: Radius.md,
  },
  iconWrap: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  content: { flex: 1, gap: 2 },
  title: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold },
  reason: { fontSize: FontSize.xs },
  tickers: { flexDirection: 'row', gap: Spacing.xs, marginTop: 4, flexWrap: 'wrap' },
  tickerPill: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: Radius.sm },
  tickerText: { fontSize: FontSize.xs, fontWeight: FontWeight.semibold, fontVariant: ['tabular-nums'] },
});
