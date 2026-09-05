import { Link, Stack } from 'expo-router';
import { StyleSheet, Text, View, useColorScheme } from 'react-native';
import { Colors } from '@/constants/Colors';

export default function NotFoundScreen() {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];

  return (
    <>
      <Stack.Screen options={{ title: 'Not found' }} />
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Screen not found</Text>
        <Link href="/(tabs)" style={{ color: colors.accent }}>Go to home</Link>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 20 },
  title: { fontSize: 20, fontWeight: 'bold', marginBottom: 12 },
});
