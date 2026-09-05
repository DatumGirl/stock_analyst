import { createClient } from '@supabase/supabase-js';
import * as SecureStore from 'expo-secure-store';
import Constants from 'expo-constants';
import { Platform } from 'react-native';

const SUPABASE_URL = Constants.expoConfig?.extra?.supabaseUrl
  ?? process.env.EXPO_PUBLIC_SUPABASE_URL
  ?? '';

const SUPABASE_ANON_KEY = Constants.expoConfig?.extra?.supabaseAnonKey
  ?? process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY
  ?? '';

// SecureStore has a 2048-byte limit per key. Supabase JWTs exceed this, so we
// split large values into numbered chunks and track the count in a meta key.
const CHUNK_SIZE = 1800;
const memoryStorage: Record<string, string> = {};

async function secureGet(key: string): Promise<string | null> {
  const countStr = await SecureStore.getItemAsync(`${key}__n`);
  if (countStr) {
    const n = parseInt(countStr, 10);
    let value = '';
    for (let i = 0; i < n; i++) {
      const chunk = await SecureStore.getItemAsync(`${key}__${i}`);
      if (chunk == null) return null;
      value += chunk;
    }
    return value;
  }
  return SecureStore.getItemAsync(key);
}

async function secureSet(key: string, value: string): Promise<void> {
  if (value.length <= CHUNK_SIZE) {
    await SecureStore.setItemAsync(key, value);
    await SecureStore.deleteItemAsync(`${key}__n`).catch(() => {});
    return;
  }
  const chunks: string[] = [];
  for (let i = 0; i < value.length; i += CHUNK_SIZE) {
    chunks.push(value.slice(i, i + CHUNK_SIZE));
  }
  await SecureStore.setItemAsync(`${key}__n`, String(chunks.length));
  await Promise.all(chunks.map((c, i) => SecureStore.setItemAsync(`${key}__${i}`, c)));
  await SecureStore.deleteItemAsync(key).catch(() => {});
}

async function secureDelete(key: string): Promise<void> {
  const countStr = await SecureStore.getItemAsync(`${key}__n`).catch(() => null);
  if (countStr) {
    const n = parseInt(countStr, 10);
    await Promise.all(
      Array.from({ length: n }, (_, i) =>
        SecureStore.deleteItemAsync(`${key}__${i}`).catch(() => {}),
      ),
    );
    await SecureStore.deleteItemAsync(`${key}__n`).catch(() => {});
  }
  await SecureStore.deleteItemAsync(key).catch(() => {});
}

const ExpoSecureStoreAdapter = {
  getItem: (key: string) =>
    Platform.OS === 'web' ? Promise.resolve(memoryStorage[key] ?? null) : secureGet(key),
  setItem: (key: string, value: string) =>
    Platform.OS === 'web' ? (void (memoryStorage[key] = value), Promise.resolve()) : secureSet(key, value),
  removeItem: (key: string) =>
    Platform.OS === 'web' ? (void delete memoryStorage[key], Promise.resolve()) : secureDelete(key),
};

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    storage: ExpoSecureStoreAdapter,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
});

export type SupabaseClient = typeof supabase;
