import React, { useState } from 'react';
import {
  View, Text, TextInput, Pressable, StyleSheet, useColorScheme,
  KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { supabase } from '@/lib/supabase';
import { Colors } from '@/constants/Colors';
import { FontSize, FontWeight, Spacing, Radius } from '@/constants/Theme';

export default function SignInScreen() {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    try {
      const fn = isSignUp
        ? supabase.auth.signUp({ email, password })
        : supabase.auth.signInWithPassword({ email, password });
      const { error: authError } = await fn;
      if (authError) throw authError;
      if (isSignUp) router.replace('/(auth)/onboarding');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: colors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <Text style={[styles.logo, { color: colors.accent }]}>StockIntel</Text>
          <Text style={[styles.tagline, { color: colors.textSecondary }]}>
            Your digital equity research team
          </Text>
        </View>

        <View style={styles.form}>
          <TextInput
            style={[styles.input, { backgroundColor: colors.card, color: colors.textPrimary, borderColor: colors.border }]}
            placeholder="Email"
            placeholderTextColor={colors.textMuted}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            value={email}
            onChangeText={setEmail}
          />
          <TextInput
            style={[styles.input, { backgroundColor: colors.card, color: colors.textPrimary, borderColor: colors.border }]}
            placeholder="Password"
            placeholderTextColor={colors.textMuted}
            secureTextEntry
            value={password}
            onChangeText={setPassword}
          />

          {error && (
            <Text style={[styles.error, { color: colors.red }]}>{error}</Text>
          )}

          <Pressable
            style={[styles.button, { backgroundColor: colors.accent, opacity: loading ? 0.7 : 1 }]}
            onPress={handleSubmit}
            disabled={loading}
            accessibilityRole="button"
          >
            {loading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.buttonText}>{isSignUp ? 'Create account' : 'Sign in'}</Text>
            }
          </Pressable>

          <Pressable onPress={() => setIsSignUp(!isSignUp)}>
            <Text style={[styles.toggle, { color: colors.textSecondary }]}>
              {isSignUp ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
            </Text>
          </Pressable>
        </View>

        <Text style={[styles.disclaimer, { color: colors.textMuted }]}>
          For research purposes only. Not investment advice.
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: Spacing.xl },
  header: { alignItems: 'center', marginBottom: Spacing.xxl * 1.5 },
  logo: { fontSize: FontSize.hero, fontWeight: FontWeight.bold },
  tagline: { fontSize: FontSize.md, marginTop: Spacing.sm },
  form: { gap: Spacing.lg },
  input: {
    height: 52,
    borderRadius: Radius.md,
    borderWidth: 1,
    paddingHorizontal: Spacing.lg,
    fontSize: FontSize.md,
  },
  error: { fontSize: FontSize.sm, textAlign: 'center' },
  button: {
    height: 52,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: { color: '#fff', fontSize: FontSize.md, fontWeight: FontWeight.semibold },
  toggle: { textAlign: 'center', fontSize: FontSize.sm, marginTop: Spacing.sm },
  disclaimer: { textAlign: 'center', fontSize: FontSize.xs, marginTop: Spacing.xxl, lineHeight: 18, fontStyle: 'italic' },
});
