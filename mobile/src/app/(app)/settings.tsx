import { Ionicons } from '@expo/vector-icons';
import { Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';

import { useAuth } from '@/lib/auth';
import { API_URL } from '@/lib/config';
import { useTheme, useThemedStyles, type ThemePreference } from '@/lib/theme';
import { radius, type Colors } from '@/theme';

const APPEARANCE: { value: ThemePreference; label: string; icon: keyof typeof Ionicons.glyphMap }[] = [
  { value: 'light', label: 'Light', icon: 'sunny-outline' },
  { value: 'dark', label: 'Dark', icon: 'moon-outline' },
  { value: 'system', label: 'System', icon: 'phone-portrait-outline' },
];

export default function SettingsScreen() {
  const { user, signOut } = useAuth();
  const { colors, isDark, preference, setPreference } = useTheme();
  const styles = useThemedStyles(makeStyles);

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <Text style={styles.sectionTitle}>Appearance</Text>
      <View style={styles.card}>
        <View style={styles.row}>
          <Ionicons name="moon-outline" size={20} color={colors.textMuted} />
          <Text style={styles.rowLabel}>Dark mode</Text>
          <Switch
            value={isDark}
            onValueChange={(on) => setPreference(on ? 'dark' : 'light')}
            trackColor={{ true: colors.primary, false: colors.border }}
            thumbColor={colors.surface}
          />
        </View>
        <View style={styles.divider} />
        <View style={styles.segmented}>
          {APPEARANCE.map((option) => {
            const selected = preference === option.value;
            return (
              <Pressable
                key={option.value}
                onPress={() => setPreference(option.value)}
                style={[styles.segment, selected && styles.segmentSelected]}
                accessibilityState={{ selected }}
              >
                <Ionicons name={option.icon} size={16} color={selected ? colors.onPrimary : colors.textMuted} />
                <Text style={[styles.segmentLabel, selected && { color: colors.onPrimary }]}>{option.label}</Text>
              </Pressable>
            );
          })}
        </View>
        <Text style={styles.hint}>“System” follows your phone’s setting.</Text>
      </View>

      <Text style={styles.sectionTitle}>Account</Text>
      <View style={styles.card}>
        <View style={styles.row}>
          <Ionicons name="person-circle-outline" size={20} color={colors.textMuted} />
          <View style={{ flex: 1 }}>
            <Text style={styles.rowLabel}>{user?.name}</Text>
            <Text style={styles.rowMeta}>{user?.email}</Text>
          </View>
        </View>
        <View style={styles.divider} />
        <Pressable style={styles.row} onPress={signOut}>
          <Ionicons name="log-out-outline" size={20} color={colors.danger} />
          <Text style={[styles.rowLabel, { color: colors.danger }]}>Sign out</Text>
        </Pressable>
      </View>

      <Text style={styles.footer}>Server: {API_URL}</Text>
    </ScrollView>
  );
}

const makeStyles = (colors: Colors) =>
  StyleSheet.create({
    screen: { flex: 1, backgroundColor: colors.background },
    content: { padding: 16, gap: 8 },
    sectionTitle: {
      fontSize: 13,
      fontWeight: '600',
      color: colors.textMuted,
      textTransform: 'uppercase',
      letterSpacing: 0.6,
      marginTop: 12,
      marginLeft: 4,
    },
    card: {
      backgroundColor: colors.surface,
      borderRadius: radius.md,
      borderWidth: StyleSheet.hairlineWidth,
      borderColor: colors.border,
      paddingHorizontal: 14,
      paddingVertical: 4,
    },
    row: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12 },
    rowLabel: { flex: 1, fontSize: 16, color: colors.text },
    rowMeta: { fontSize: 13, color: colors.textMuted, marginTop: 2 },
    divider: { height: StyleSheet.hairlineWidth, backgroundColor: colors.border },
    segmented: {
      flexDirection: 'row',
      backgroundColor: colors.surfaceMuted,
      borderRadius: radius.sm,
      padding: 3,
      marginTop: 12,
    },
    segment: {
      flex: 1,
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 6,
      paddingVertical: 8,
      borderRadius: radius.sm - 2,
    },
    segmentSelected: { backgroundColor: colors.primary },
    segmentLabel: { fontSize: 14, fontWeight: '500', color: colors.textMuted },
    hint: { fontSize: 13, color: colors.textMuted, marginTop: 8, marginBottom: 10 },
    footer: { fontSize: 12, color: colors.textMuted, textAlign: 'center', marginTop: 16 },
  });
