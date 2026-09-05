import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, Pressable,
  useColorScheme, Switch, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuthStore } from '@/stores/authStore';
import { useProfile, useUpdateProfile } from '@/hooks/useProfile';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing, Radius } from '@/constants/Theme';
import type { RiskTolerance } from '@/lib/types';

const RISK_LABELS: Record<RiskTolerance, string> = {
  conservative: 'Conservative',
  moderate: 'Moderate',
  aggressive: 'Aggressive',
};

export default function MeScreen() {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const { user, signOut } = useAuthStore();
  const { data: profile } = useProfile(user?.id ?? null);
  const { mutate: updateProfile } = useUpdateProfile();

  function handleSignOut() {
    Alert.alert('Sign out', 'Are you sure?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign out', style: 'destructive', onPress: signOut },
    ]);
  }

  function toggleNotifications(value: boolean) {
    if (!user) return;
    updateProfile({ user_id: user.id, notifications_enabled: value });
  }

  const rows: Array<{ label: string; value: string | null; icon: keyof typeof Ionicons.glyphMap }> = [
    { label: 'Risk tolerance', value: profile ? RISK_LABELS[profile.risk_tolerance] : null, icon: 'shield-outline' },
    { label: 'Target CAGR', value: profile ? `${(profile.target_cagr * 100).toFixed(0)}%` : null, icon: 'trending-up-outline' },
    { label: 'Horizon', value: profile ? `${profile.horizon_years} year${profile.horizon_years !== 1 ? 's' : ''}` : null, icon: 'calendar-outline' },
    { label: 'Daily brief time', value: profile?.brief_time ?? null, icon: 'time-outline' },
  ];

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Me</Text>

        {/* Account */}
        <View style={[styles.section, { backgroundColor: colors.card }]}>
          <View style={styles.accountRow}>
            <View style={[styles.avatar, { backgroundColor: colors.accent + '22' }]}>
              <Ionicons name="person" size={28} color={colors.accent} />
            </View>
            <View style={styles.accountInfo}>
              <Text style={[styles.accountEmail, { color: colors.textPrimary }]} numberOfLines={1}>
                {user?.email ?? '—'}
              </Text>
              <Text style={[styles.accountSub, { color: colors.textMuted }]}>Signed in</Text>
            </View>
          </View>
        </View>

        {/* Goals */}
        <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>Goals & profile</Text>
        <View style={[styles.section, { backgroundColor: colors.card }]}>
          {rows.map((row, i) => (
            <View
              key={row.label}
              style={[
                styles.row,
                i < rows.length - 1 && { borderBottomColor: colors.border, borderBottomWidth: 1 },
              ]}
            >
              <Ionicons name={row.icon} size={18} color={colors.textSecondary} />
              <Text style={[styles.rowLabel, { color: colors.textSecondary }]}>{row.label}</Text>
              <Text style={[styles.rowValue, { color: colors.textPrimary }]}>{row.value ?? '—'}</Text>
            </View>
          ))}
        </View>

        {/* Notifications */}
        <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>Notifications</Text>
        <View style={[styles.section, { backgroundColor: colors.card }]}>
          <View style={styles.row}>
            <Ionicons name="notifications-outline" size={18} color={colors.textSecondary} />
            <Text style={[styles.rowLabel, { color: colors.textSecondary }]}>Daily brief push</Text>
            <Switch
              value={profile?.notifications_enabled ?? false}
              onValueChange={toggleNotifications}
              trackColor={{ true: colors.accent }}
            />
          </View>
        </View>

        {/* Disclaimer */}
        <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>Legal</Text>
        <View style={[styles.section, { backgroundColor: colors.card }]}>
          <View style={[styles.disclaimerBox]}>
            <Text style={[styles.disclaimerText, { color: colors.textMuted }]}>
              StockIntel provides research and analysis only. Nothing here constitutes investment advice or a recommendation to buy or sell any security. All numbers originate from deterministic engines and third-party data sources.
            </Text>
          </View>
        </View>

        {/* Sign out */}
        <Pressable
          style={[styles.signOutBtn, { borderColor: colors.border }]}
          onPress={handleSignOut}
        >
          <Ionicons name="log-out-outline" size={18} color={colors.red} />
          <Text style={[styles.signOutText, { color: colors.red }]}>Sign out</Text>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: 40 },
  title: { fontSize: FontSize.xxl, fontWeight: FontWeight.bold, marginBottom: Spacing.md },
  sectionLabel: { fontSize: FontSize.xs, textTransform: 'uppercase', letterSpacing: 0.8, marginTop: Spacing.sm },
  section: { borderRadius: Radius.lg, overflow: 'hidden' },
  accountRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.lg, padding: Spacing.lg },
  avatar: { width: 52, height: 52, borderRadius: 26, alignItems: 'center', justifyContent: 'center' },
  accountInfo: { flex: 1 },
  accountEmail: { fontSize: FontSize.md, fontWeight: FontWeight.semibold },
  accountSub: { fontSize: FontSize.xs, marginTop: 2 },
  row: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, padding: Spacing.lg },
  rowLabel: { flex: 1, fontSize: FontSize.sm },
  rowValue: { fontSize: FontSize.sm, fontWeight: FontWeight.semibold },
  disclaimerBox: { padding: Spacing.lg },
  disclaimerText: { fontSize: FontSize.xs, lineHeight: 20, fontStyle: 'italic' },
  signOutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    padding: Spacing.lg,
    borderRadius: Radius.lg,
    borderWidth: 1,
    marginTop: Spacing.md,
  },
  signOutText: { fontSize: FontSize.md, fontWeight: FontWeight.semibold },
});
