import React, { useEffect, useRef } from 'react';
import { View, Animated, StyleSheet, useColorScheme, ViewStyle } from 'react-native';
import { Colors } from '@/constants/Colors';
import { Radius, Spacing } from '@/constants/Theme';

interface Props {
  height?: number;
  width?: number | string;
  style?: ViewStyle;
}

export function SkeletonCard({ height = 80, width = '100%', style }: Props) {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const anim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(anim, { toValue: 1, duration: 800, useNativeDriver: true }),
        Animated.timing(anim, { toValue: 0, duration: 800, useNativeDriver: true }),
      ]),
    ).start();
  }, [anim]);

  const opacity = anim.interpolate({ inputRange: [0, 1], outputRange: [0.3, 0.7] });

  return (
    <Animated.View
      style={[
        styles.card,
        { height, width, backgroundColor: colors.border, opacity },
        style,
      ]}
      accessibilityLabel="Loading"
    />
  );
}

export function SkeletonGroup({ count = 3 }: { count?: number }) {
  return (
    <View style={styles.group}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} height={72 + (i % 2) * 16} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: Radius.md },
  group: { gap: Spacing.md },
});
