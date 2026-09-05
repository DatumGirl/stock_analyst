import React, { useState } from 'react';
import {
  View, Text, StyleSheet, Pressable, useColorScheme,
  ScrollView, Switch, ActivityIndicator, Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { supabase } from '@/lib/supabase';
import { useAuthStore } from '@/stores/authStore';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing, Radius } from '@/constants/Theme';
import type { RiskTolerance } from '@/lib/types';

const RISK_OPTIONS: { value: RiskTolerance; label: string; desc: string }[] = [
  { value: 'conservative', label: 'Conservative', desc: 'Capital preservation over growth. Low volatility.' },
  { value: 'moderate', label: 'Moderate', desc: 'Balanced between growth and stability.' },
  { value: 'aggressive', label: 'Aggressive', desc: 'Maximum long-term growth. Higher volatility accepted.' },
];

const CAGR_OPTIONS = [8, 10, 12, 15, 20];

export default function OnboardingScreen() {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const router = useRouter();
  const { user } = useAuthStore();

  const [step, setStep] = useState(1);
  const [riskTolerance, setRiskTolerance] = useState<RiskTolerance>('moderate');
  const [targetCagr, setTargetCagr] = useState(12);
  const [horizonYears, setHorizonYears] = useState(3);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [disclaimerAcknowledged, setDisclaimerAcknowledged] = useState(false);
  const [loading, setLoading] = useState(false);

  async function finishOnboarding() {
    setLoading(true);
    try {
      // Store may not be populated yet if we navigated here immediately after signUp
      const userId = user?.id ?? (await supabase.auth.getUser()).data.user?.id;
      if (!userId) {
        Alert.alert('Session error', 'Could not find your account. Please sign in again.');
        router.replace('/(auth)/sign-in');
        return;
      }

      const { error: profileError } = await supabase.from('profiles').upsert({
        user_id: userId,
        risk_tolerance: riskTolerance,
        target_cagr: targetCagr / 100,
        horizon_years: horizonYears,
        notifications_enabled: notificationsEnabled,
        disclaimer_acknowledged: disclaimerAcknowledged,
        brief_time: '06:00',
      });
      if (profileError) throw profileError;

      const { error: portfolioError } = await supabase.from('portfolios').insert({
        user_id: userId,
        name: 'My Portfolio',
      });
      // Ignore duplicate portfolio (user may have tapped twice)
      if (portfolioError && !portfolioError.message.includes('duplicate')) {
        throw portfolioError;
      }

      router.replace('/(tabs)');
    } catch (e: unknown) {
      Alert.alert('Setup failed', e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      {/* Progress dots */}
      <View style={styles.progress}>
        {[1, 2, 3, 4].map((s) => (
          <View
            key={s}
            style={[
              styles.dot,
              { backgroundColor: s <= step ? colors.accent : colors.border },
            ]}
          />
        ))}
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {step === 1 && (
          <View style={styles.step}>
            <Text style={[styles.title, { color: colors.textPrimary }]}>
              What's your risk tolerance?
            </Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              This shapes how the platform evaluates portfolio risk for you.
            </Text>
            <View style={styles.options}>
              {RISK_OPTIONS.map((opt) => (
                <Pressable
                  key={opt.value}
                  style={[
                    styles.optionCard,
                    {
                      backgroundColor: riskTolerance === opt.value ? colors.accent + '22' : colors.card,
                      borderColor: riskTolerance === opt.value ? colors.accent : colors.border,
                    },
                  ]}
                  onPress={() => setRiskTolerance(opt.value)}
                >
                  <Text style={[styles.optionLabel, { color: colors.textPrimary }]}>{opt.label}</Text>
                  <Text style={[styles.optionDesc, { color: colors.textSecondary }]}>{opt.desc}</Text>
                </Pressable>
              ))}
            </View>
          </View>
        )}

        {step === 2 && (
          <View style={styles.step}>
            <Text style={[styles.title, { color: colors.textPrimary }]}>
              What's your return goal?
            </Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              Target annual return. The platform tracks your probability of achieving this.
            </Text>

            <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>Target CAGR</Text>
            <View style={styles.options}>
              {CAGR_OPTIONS.map((pct) => (
                <Pressable
                  key={pct}
                  style={[
                    styles.cagrChip,
                    {
                      backgroundColor: targetCagr === pct ? colors.accent : colors.card,
                      borderColor: targetCagr === pct ? colors.accent : colors.border,
                    },
                  ]}
                  onPress={() => setTargetCagr(pct)}
                >
                  <Text style={[styles.cagrText, { color: targetCagr === pct ? '#fff' : colors.textPrimary }]}>
                    {pct}%
                  </Text>
                </Pressable>
              ))}
            </View>

            <Text style={[styles.sectionLabel, { color: colors.textMuted, marginTop: Spacing.xl }]}>
              Horizon: {horizonYears} year{horizonYears !== 1 ? 's' : ''}
            </Text>
            <View style={styles.options}>
              {[1, 2, 3, 5, 10].map((y) => (
                <Pressable
                  key={y}
                  style={[
                    styles.cagrChip,
                    {
                      backgroundColor: horizonYears === y ? colors.accent : colors.card,
                      borderColor: horizonYears === y ? colors.accent : colors.border,
                    },
                  ]}
                  onPress={() => setHorizonYears(y)}
                >
                  <Text style={[styles.cagrText, { color: horizonYears === y ? '#fff' : colors.textPrimary }]}>
                    {y}y
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>
        )}

        {step === 3 && (
          <View style={styles.step}>
            <Text style={[styles.title, { color: colors.textPrimary }]}>
              Set up your portfolio
            </Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              You can add holdings now or start with just a watchlist. We'll create a default portfolio for you.
            </Text>
            <View style={[styles.infoCard, { backgroundColor: colors.card, borderColor: colors.border }]}>
              <Text style={[styles.optionLabel, { color: colors.textPrimary }]}>Default portfolio created</Text>
              <Text style={[styles.optionDesc, { color: colors.textSecondary }]}>
                Add positions after sign-in from the Portfolio tab.
              </Text>
            </View>

            <View style={styles.notifRow}>
              <View style={styles.notifText}>
                <Text style={[styles.optionLabel, { color: colors.textPrimary }]}>Daily brief notifications</Text>
                <Text style={[styles.optionDesc, { color: colors.textSecondary }]}>
                  One push each morning with your portfolio summary.
                </Text>
              </View>
              <Switch
                value={notificationsEnabled}
                onValueChange={setNotificationsEnabled}
                trackColor={{ true: colors.accent }}
              />
            </View>
          </View>
        )}

        {step === 4 && (
          <View style={styles.step}>
            <Text style={[styles.title, { color: colors.textPrimary }]}>
              Important disclaimer
            </Text>
            <View style={[styles.disclaimerBox, { backgroundColor: colors.card, borderColor: colors.border }]}>
              <Text style={[styles.disclaimerText, { color: colors.textSecondary }]}>
                StockIntel is a research and analysis tool, not a licensed financial advisor.{'\n\n'}
                All analysis, scores, probabilities, and signals are for informational purposes only. They do not constitute investment advice, a recommendation to buy or sell any security, or a guarantee of any outcome.{'\n\n'}
                All numbers originate from deterministic engines or third-party data providers, never from AI model estimation.{'\n\n'}
                Past performance is not indicative of future results. You are solely responsible for your investment decisions.
              </Text>
            </View>
            <Pressable
              style={[styles.checkRow]}
              onPress={() => setDisclaimerAcknowledged(!disclaimerAcknowledged)}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: disclaimerAcknowledged }}
            >
              <View style={[
                styles.checkbox,
                {
                  backgroundColor: disclaimerAcknowledged ? colors.accent : 'transparent',
                  borderColor: disclaimerAcknowledged ? colors.accent : colors.border,
                },
              ]} />
              <Text style={[styles.checkLabel, { color: colors.textSecondary }]}>
                I understand this is not investment advice
              </Text>
            </Pressable>
          </View>
        )}
      </ScrollView>

      <View style={[styles.footer, { borderTopColor: colors.border }]}>
        {step > 1 && (
          <Pressable
            style={[styles.secondaryBtn, { borderColor: colors.border }]}
            onPress={() => setStep(step - 1)}
          >
            <Text style={[styles.secondaryBtnText, { color: colors.textSecondary }]}>Back</Text>
          </Pressable>
        )}
        <Pressable
          style={[
            styles.primaryBtn,
            {
              backgroundColor: colors.accent,
              flex: step > 1 ? 1 : undefined,
              opacity: (step === 4 && !disclaimerAcknowledged) || loading ? 0.5 : 1,
            },
          ]}
          onPress={step < 4 ? () => setStep(step + 1) : finishOnboarding}
          disabled={(step === 4 && !disclaimerAcknowledged) || loading}
        >
          {loading
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.primaryBtnText}>{step < 4 ? 'Continue' : "Let's go"}</Text>
          }
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  progress: { flexDirection: 'row', gap: Spacing.sm, justifyContent: 'center', paddingTop: 60, paddingBottom: Spacing.xl },
  dot: { width: 8, height: 8, borderRadius: 4 },
  content: { padding: Spacing.xl, flexGrow: 1 },
  step: { gap: Spacing.lg },
  title: { fontSize: FontSize.xxl, fontWeight: FontWeight.bold },
  subtitle: { fontSize: FontSize.md, lineHeight: 24 },
  sectionLabel: { fontSize: FontSize.xs, textTransform: 'uppercase', letterSpacing: 0.8 },
  options: { gap: Spacing.md },
  optionCard: {
    padding: Spacing.lg,
    borderRadius: Radius.md,
    borderWidth: 1.5,
    gap: Spacing.xs,
  },
  optionLabel: { fontSize: FontSize.md, fontWeight: FontWeight.semibold },
  optionDesc: { fontSize: FontSize.sm, lineHeight: 20 },
  cagrChip: {
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    borderRadius: Radius.full,
    borderWidth: 1,
    alignItems: 'center',
  },
  cagrText: { fontSize: FontSize.lg, fontWeight: FontWeight.bold },
  infoCard: { padding: Spacing.lg, borderRadius: Radius.md, borderWidth: 1, gap: Spacing.xs },
  notifRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.lg },
  notifText: { flex: 1, gap: Spacing.xs },
  disclaimerBox: { padding: Spacing.lg, borderRadius: Radius.md, borderWidth: 1 },
  disclaimerText: { fontSize: FontSize.sm, lineHeight: 22 },
  checkRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md, marginTop: Spacing.md },
  checkbox: { width: 22, height: 22, borderRadius: Radius.sm, borderWidth: 2 },
  checkLabel: { flex: 1, fontSize: FontSize.sm },
  footer: {
    flexDirection: 'row',
    gap: Spacing.md,
    padding: Spacing.xl,
    paddingBottom: 40,
    borderTopWidth: 1,
  },
  primaryBtn: {
    minWidth: 160,
    height: 52,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryBtnText: { color: '#fff', fontSize: FontSize.md, fontWeight: FontWeight.semibold },
  secondaryBtn: {
    height: 52,
    paddingHorizontal: Spacing.xl,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  secondaryBtnText: { fontSize: FontSize.md },
});
