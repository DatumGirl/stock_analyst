import { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useColorScheme } from 'react-native';
import * as SplashScreen from 'expo-splash-screen';
import { supabase } from '@/lib/supabase';
import { useAuthStore } from '@/stores/authStore';
import { usePortfolioStore } from '@/stores/portfolioStore';

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

function AuthGuard() {
  const { session, setSession, isLoading } = useAuthStore();
  const { loadPortfolios } = usePortfolioStore();
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      if (data.session?.user) {
        loadPortfolios(data.session.user.id);
      }
      SplashScreen.hideAsync();
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      if (s?.user) {
        loadPortfolios(s.user.id);
      }
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (isLoading) return;
    const inAuth = segments[0] === '(auth)';
    const inOnboarding = segments[1] === 'onboarding';
    if (!session && !inAuth) {
      router.replace('/(auth)/sign-in');
    } else if (session && inAuth && !inOnboarding) {
      // Let onboarding complete before redirecting
      router.replace('/(tabs)');
    }
  }, [session, isLoading, segments]);

  return null;
}

export default function RootLayout() {
  const scheme = useColorScheme();

  return (
    <QueryClientProvider client={queryClient}>
      <AuthGuard />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen
          name="ticker/[symbol]"
          options={{ presentation: 'card', headerShown: false }}
        />
        <Stack.Screen
          name="compare"
          options={{ presentation: 'modal', headerShown: false }}
        />
        <Stack.Screen
          name="add-position"
          options={{ presentation: 'modal', headerShown: false }}
        />
        <Stack.Screen
          name="create-portfolio"
          options={{ presentation: 'modal', headerShown: false }}
        />
      </Stack>
    </QueryClientProvider>
  );
}
