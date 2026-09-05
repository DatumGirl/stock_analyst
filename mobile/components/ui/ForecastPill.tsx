import React from 'react';
import { View, Text, StyleSheet, useColorScheme } from 'react-native';
import { Colors } from '@/constants/Colors';
import { FontSize, Spacing, Radius } from '@/constants/Theme';

type Variant = 'forecast' | 'fact';

interface Props {
  variant?: Variant;
  label?: string;
}

export function ForecastPill({ variant = 'forecast', label }: Props) {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];

  const isForecast = variant === 'forecast';
  const bg = isForecast ? colors.forecast + '22' : colors.accent + '22';
  const fg = isForecast ? colors.forecast : colors.accent;
  const text = label ?? (isForecast ? 'forecast' : 'fact');

  return (
    <View style={[styles.pill, { backgroundColor: bg, borderColor: fg + '44' }]}>
      <Text style={[styles.label, { color: fg }]}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: Radius.full,
    borderWidth: 1,
    alignSelf: 'flex-start',
  },
  label: { fontSize: FontSize.xs, fontWeight: '600', letterSpacing: 0.2, textTransform: 'lowercase' },
});
