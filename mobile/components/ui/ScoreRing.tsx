import React from 'react';
import { View, Text, StyleSheet, useColorScheme } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, ScoreBand } from '@/constants/Theme';

interface Props {
  score: number;        // 0–100
  size?: number;
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
}

function bandColor(score: number, scheme: 'light' | 'dark'): string {
  const c = Colors[scheme];
  if (score >= ScoreBand.good) return c.green;
  if (score >= ScoreBand.ok) return c.amber;
  return c.red;
}

export function ScoreRing({ score, size = 80, strokeWidth = 8, label, sublabel }: Props) {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(Math.max(score, 0), 100) / 100;
  const dashOffset = circumference * (1 - progress);
  const color = bandColor(score, scheme);

  return (
    <View style={styles.container} accessibilityLabel={`Score ${score} out of 100`}>
      <Svg width={size} height={size}>
        {/* Track */}
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={colors.border}
          strokeWidth={strokeWidth}
          fill="none"
        />
        {/* Progress */}
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          rotation="-90"
          origin={`${size / 2}, ${size / 2}`}
        />
      </Svg>
      <View style={[styles.center, { width: size, height: size }]}>
        <Text style={[styles.score, { color, fontSize: size * 0.28 }]}>
          {Math.round(score)}
        </Text>
        {label && (
          <Text style={[styles.label, { color: colors.textSecondary, fontSize: size * 0.14 }]}>
            {label}
          </Text>
        )}
      </View>
      {sublabel && (
        <Text style={[styles.sublabel, { color: colors.textMuted }]}>{sublabel}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center' },
  center: { position: 'absolute', alignItems: 'center', justifyContent: 'center' },
  score: { fontWeight: FontWeight.bold, fontVariant: ['tabular-nums'] },
  label: { marginTop: 1 },
  sublabel: { marginTop: 4, fontSize: FontSize.xs },
});
