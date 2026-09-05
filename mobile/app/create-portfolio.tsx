import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, Pressable,
  useColorScheme, KeyboardAvoidingView, Platform,
  ActivityIndicator, Alert, ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { supabase } from '@/lib/supabase';
import { useAuthStore } from '@/stores/authStore';
import { usePortfolioStore } from '@/stores/portfolioStore';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing, Radius } from '@/constants/Theme';

type PortfolioType = 'short_term' | 'long_term' | 'custom';

const PORTFOLIO_TYPES: { value: PortfolioType; label: string; icon: string; desc: string; defaultName: string }[] = [
  {
    value: 'short_term',
    label: 'Short Term',
    icon: 'flash-outline',
    desc: 'Active trades, swing positions, 0–12 months.',
    defaultName: 'Short Term',
  },
  {
    value: 'long_term',
    label: 'Long Term',
    icon: 'trending-up-outline',
    desc: 'Buy-and-hold, compounding over 1–10+ years.',
    defaultName: 'Long Term',
  },
  {
    value: 'custom',
    label: 'Custom',
    icon: 'create-outline',
    desc: 'Name it yourself — thematic, sector, or strategy.',
    defaultName: '',
  },
];

export default function CreatePortfolioScreen() {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const router = useRouter();
  const queryClient = useQueryClient();

  const { user } = useAuthStore();
  const { loadPortfolios, setActivePortfolio } = usePortfolioStore();

  const [portfolioType, setPortfolioType] = useState<PortfolioType>('long_term');
  const [name, setName] = useState('Long Term');
  const [loading, setLoading] = useState(false);

  function selectType(type: PortfolioType) {
    setPortfolioType(type);
    const preset = PORTFOLIO_TYPES.find((t) => t.value === type);
    if (preset?.defaultName) setName(preset.defaultName);
    else setName('');
  }

  async function handleCreate() {
    const trimmed = name.trim();
    if (!trimmed) return Alert.alert('Name required', 'Give your portfolio a name.');

    const userId = user?.id ?? (await supabase.auth.getUser()).data.user?.id;
    if (!userId) return Alert.alert('Session error', 'Please sign in again.');

    setLoading(true);
    try {
      const { data, error } = await supabase
        .from('portfolios')
        .insert({ user_id: userId, name: trimmed })
        .select()
        .single();
      if (error) throw error;

      // Reload portfolios and activate the new one
      await loadPortfolios(userId);
      setActivePortfolio(data.id);

      // Bust any stale snapshot/position queries
      queryClient.removeQueries({ queryKey: ['snapshot'] });
      queryClient.removeQueries({ queryKey: ['positions'] });

      router.back();
    } catch (e: unknown) {
      Alert.alert('Failed', e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['top', 'bottom']}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {/* Header */}
          <View style={styles.header}>
            <Pressable onPress={() => router.back()} hitSlop={12}>
              <Ionicons name="chevron-back" size={24} color={colors.textPrimary} />
            </Pressable>
            <Text style={[styles.title, { color: colors.textPrimary }]}>New portfolio</Text>
            <View style={{ width: 24 }} />
          </View>

          {/* Type selector */}
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>TYPE</Text>
          <View style={styles.typeList}>
            {PORTFOLIO_TYPES.map((t) => (
              <Pressable
                key={t.value}
                style={[
                  styles.typeCard,
                  {
                    backgroundColor: portfolioType === t.value ? colors.accent + '18' : colors.card,
                    borderColor: portfolioType === t.value ? colors.accent : colors.border,
                  },
                ]}
                onPress={() => selectType(t.value)}
              >
                <View style={styles.typeRow}>
                  <Ionicons
                    name={t.icon as any}
                    size={20}
                    color={portfolioType === t.value ? colors.accent : colors.textSecondary}
                  />
                  <View style={{ flex: 1 }}>
                    <Text style={[styles.typeLabel, { color: portfolioType === t.value ? colors.accent : colors.textPrimary }]}>
                      {t.label}
                    </Text>
                    <Text style={[styles.typeDesc, { color: colors.textMuted }]}>{t.desc}</Text>
                  </View>
                  {portfolioType === t.value && (
                    <Ionicons name="checkmark-circle" size={20} color={colors.accent} />
                  )}
                </View>
              </Pressable>
            ))}
          </View>

          {/* Name */}
          <Text style={[styles.sectionLabel, { color: colors.textMuted, marginTop: Spacing.xl }]}>NAME</Text>
          <TextInput
            style={[styles.input, { backgroundColor: colors.card, color: colors.textPrimary, borderColor: colors.border }]}
            placeholder="Portfolio name"
            placeholderTextColor={colors.textMuted}
            value={name}
            onChangeText={setName}
            autoCorrect={false}
            maxLength={40}
          />
          <Text style={[styles.hint, { color: colors.textMuted }]}>
            {name.trim().length}/40 characters
          </Text>
        </ScrollView>

        {/* Footer */}
        <View style={[styles.footer, { borderTopColor: colors.border }]}>
          <Pressable
            style={[styles.btn, { backgroundColor: colors.accent, opacity: loading ? 0.7 : 1 }]}
            onPress={handleCreate}
            disabled={loading}
          >
            {loading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.btnText}>Create portfolio</Text>}
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { padding: Spacing.xl, gap: Spacing.md, flexGrow: 1 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: Spacing.lg },
  title: { fontSize: FontSize.xl, fontWeight: FontWeight.bold },
  sectionLabel: { fontSize: FontSize.xs, fontWeight: FontWeight.semibold, letterSpacing: 0.8, textTransform: 'uppercase' },
  typeList: { gap: Spacing.sm },
  typeCard: { padding: Spacing.lg, borderRadius: Radius.md, borderWidth: 1.5 },
  typeRow: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.md },
  typeLabel: { fontSize: FontSize.md, fontWeight: FontWeight.semibold, marginBottom: 2 },
  typeDesc: { fontSize: FontSize.sm, lineHeight: 18 },
  input: {
    height: 52,
    borderRadius: Radius.md,
    borderWidth: 1,
    paddingHorizontal: Spacing.lg,
    fontSize: FontSize.md,
  },
  hint: { fontSize: FontSize.xs, textAlign: 'right', marginTop: -Spacing.sm },
  footer: { padding: Spacing.xl, paddingBottom: 32, borderTopWidth: 1 },
  btn: { height: 52, borderRadius: Radius.md, alignItems: 'center', justifyContent: 'center' },
  btnText: { color: '#fff', fontSize: FontSize.md, fontWeight: FontWeight.semibold },
});
