import React from 'react';
import { View, Text, StyleSheet, useColorScheme } from 'react-native';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing } from '@/constants/Theme';

interface Props {
  low: number;
  base: number;
  high: number;
  bear?: number;
  bull?: number;
  current?: number;
  currency?: string;
  label?: string;
}

function fmt(val: number, currency = '$') {
  return `${currency}${val.toFixed(0)}`;
}

export function RangeBar({ low, base, high, bear, bull, current, currency = '$', label }: Props) {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];

  const rangeMin = bear ?? low;
  const rangeMax = bull ?? high;
  const span = rangeMax - rangeMin || 1;

  const pct = (v: number) => Math.min(Math.max((v - rangeMin) / span, 0), 1) * 100;

  return (
    <View style={styles.container}>
      {label && <Text style={[styles.label, { color: colors.textSecondary }]}>{label}</Text>}

      <View style={[styles.track, { backgroundColor: colors.border }]}>
        {/* Range band (low→high) */}
        <View
          style={[
            styles.band,
            {
              left: `${pct(low)}%`,
              width: `${pct(high) - pct(low)}%`,
              backgroundColor: colors.accent + '33',
            },
          ]}
        />
        {/* Base marker */}
        <View style={[styles.marker, { left: `${pct(base)}%`, backgroundColor: colors.accent }]} />
        {/* Current price marker */}
        {current !== undefined && (
          <View
            style={[
              styles.currentMarker,
              { left: `${pct(current)}%`, borderColor: colors.textPrimary },
            ]}
          />
        )}
      </View>

      <View style={styles.labels}>
        <Text style={[styles.labelText, { color: colors.textSecondary }]}>
          Bear {fmt(rangeMin, currency)}
        </Text>
        <Text style={[styles.labelText, { color: colors.accent, fontWeight: FontWeight.semibold }]}>
          Base {fmt(base, currency)}
        </Text>
        <Text style={[styles.labelText, { color: colors.textSecondary }]}>
          Bull {fmt(rangeMax, currency)}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: Spacing.sm },
  label: { fontSize: FontSize.sm },
  track: {
    height: 8,
    borderRadius: 4,
    position: 'relative',
    overflow: 'visible',
  },
  band: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    borderRadius: 4,
  },
  marker: {
    position: 'absolute',
    width: 3,
    top: -4,
    bottom: -4,
    borderRadius: 2,
    marginLeft: -1.5,
  },
  currentMarker: {
    position: 'absolute',
    width: 14,
    height: 14,
    borderRadius: 7,
    borderWidth: 2,
    backgroundColor: 'transparent',
    top: -3,
    marginLeft: -7,
  },
  labels: { flexDirection: 'row', justifyContent: 'space-between' },
  labelText: { fontSize: FontSize.xs },
});
