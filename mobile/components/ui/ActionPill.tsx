import React from 'react';
import { View, Text, StyleSheet, useColorScheme } from 'react-native';
import { Colors } from '@/constants/Colors';
import { FontSize, Spacing, Radius, FontWeight } from '@/constants/Theme';
import type { ActionRecommendation } from '@/lib/types';

interface Props {
  action: ActionRecommendation;
  size?: 'sm' | 'md';
}

function actionStyle(action: ActionRecommendation, scheme: 'light' | 'dark') {
  const c = Colors[scheme];
  switch (action) {
    case 'Watch': return { bg: c.accent + '22', fg: c.accent };
    case 'Hold': return { bg: c.green + '22', fg: c.green };
    case 'Research': return { bg: c.forecast + '22', fg: c.forecast };
    case 'Avoid': return { bg: c.red + '22', fg: c.red };
  }
}

export function ActionPill({ action, size = 'md' }: Props) {
  const scheme = useColorScheme() ?? 'dark';
  const { bg, fg } = actionStyle(action, scheme);
  const isSmall = size === 'sm';

  return (
    <View style={[
      styles.pill,
      { backgroundColor: bg, paddingHorizontal: isSmall ? Spacing.sm : Spacing.md, paddingVertical: isSmall ? 2 : Spacing.xs },
    ]}>
      <Text style={[styles.label, { color: fg, fontSize: isSmall ? FontSize.xs : FontSize.sm }]}>
        {action}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: { borderRadius: Radius.full, alignSelf: 'flex-start' },
  label: { fontWeight: FontWeight.semibold },
});
