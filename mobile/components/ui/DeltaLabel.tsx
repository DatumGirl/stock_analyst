import React from 'react';
import { Text, StyleSheet, useColorScheme } from 'react-native';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight } from '@/constants/Theme';

interface Props {
  value: number | string;
  change?: number;
  changePct?: number;
  size?: 'sm' | 'md' | 'lg';
  showArrow?: boolean;
}

const SIZE_MAP = { sm: FontSize.sm, md: FontSize.md, lg: FontSize.xl };

export function DeltaLabel({ value, change, changePct, size = 'md', showArrow = true }: Props) {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];

  const delta = changePct ?? (typeof change === 'number' ? change : null);
  const isPositive = delta !== null && delta > 0;
  const isNegative = delta !== null && delta < 0;

  const color = isPositive ? colors.green : isNegative ? colors.red : colors.textSecondary;
  const arrow = isPositive ? '↑' : isNegative ? '↓' : '';
  const fontSize = SIZE_MAP[size];

  const deltaText =
    delta !== null
      ? `${showArrow ? arrow : ''} ${Math.abs(delta * 100).toFixed(2)}%`.trim()
      : null;

  return (
    <Text style={[styles.text, { fontSize }]}>
      <Text style={{ color: colors.textPrimary, fontVariant: ['tabular-nums'] }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </Text>
      {deltaText && (
        <Text style={{ color, opacity: Math.min(1, 0.5 + Math.abs(delta ?? 0) * 5) }}>
          {'  '}{deltaText}
        </Text>
      )}
    </Text>
  );
}

const styles = StyleSheet.create({
  text: { fontWeight: FontWeight.semibold },
});
