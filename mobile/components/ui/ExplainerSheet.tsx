import React from 'react';
import { View, Text, StyleSheet, Pressable, Modal, useColorScheme, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '@/constants/Colors';
import { FontSize, Spacing, Radius, FontWeight } from '@/constants/Theme';

interface Props {
  term: string;
  explanation: string;
  whyItMatters?: string;
  visible: boolean;
  onClose: () => void;
}

export function ExplainerSheet({ term, explanation, whyItMatters, visible, onClose }: Props) {
  const scheme = useColorScheme() ?? 'dark';
  const colors = Colors[scheme];

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} />
      <View style={[styles.sheet, { backgroundColor: colors.surface }]}>
        <View style={[styles.handle, { backgroundColor: colors.border }]} />

        <View style={styles.header}>
          <Text style={[styles.term, { color: colors.textPrimary }]}>{term}</Text>
          <Pressable onPress={onClose} hitSlop={8} accessibilityLabel="Close">
            <Ionicons name="close" size={22} color={colors.textSecondary} />
          </Pressable>
        </View>

        <ScrollView showsVerticalScrollIndicator={false}>
          <Text style={[styles.explanation, { color: colors.textSecondary }]}>{explanation}</Text>
          {whyItMatters && (
            <>
              <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>Why it matters</Text>
              <Text style={[styles.explanation, { color: colors.textSecondary }]}>{whyItMatters}</Text>
            </>
          )}
          <Text style={[styles.disclaimer, { color: colors.textMuted }]}>
            Not investment advice. All analysis is research only.
          </Text>
        </ScrollView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)' },
  sheet: {
    borderTopLeftRadius: Radius.lg,
    borderTopRightRadius: Radius.lg,
    padding: Spacing.xl,
    paddingTop: Spacing.md,
    maxHeight: '70%',
  },
  handle: { width: 36, height: 4, borderRadius: 2, alignSelf: 'center', marginBottom: Spacing.lg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: Spacing.lg },
  term: { fontSize: FontSize.xl, fontWeight: FontWeight.bold },
  explanation: { fontSize: FontSize.md, lineHeight: 24, marginBottom: Spacing.lg },
  sectionLabel: { fontSize: FontSize.xs, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: Spacing.sm },
  disclaimer: { fontSize: FontSize.xs, marginTop: Spacing.xl, lineHeight: 18, fontStyle: 'italic' },
});
