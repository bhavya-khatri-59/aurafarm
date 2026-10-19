import { Ionicons } from '@expo/vector-icons';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';

import { useTheme, useThemedStyles } from '@/lib/theme';
import type { Diagnosis } from '@/lib/types';
import { radius, type Colors } from '@/theme';

const percent = (value: number) => `${Math.round(value * 100)}%`;

export function DiagnosisCard({ diagnosis }: { diagnosis: Diagnosis }) {
  const { colors } = useTheme();
  const styles = useThemedStyles(makeStyles);
  const uncertain = diagnosis.status === 'uncertain';
  const weather = diagnosis.weather && !diagnosis.weather.error ? diagnosis.weather : null;
  const outbreak = diagnosis.outbreaks?.by_disease.find((d) => d.label === diagnosis.label);

  return (
    <View style={[styles.card, uncertain && styles.cardUncertain]}>
      <View style={styles.header}>
        <Ionicons
          name={uncertain ? 'help-circle' : diagnosis.is_healthy ? 'checkmark-circle' : 'leaf'}
          size={22}
          color={uncertain ? colors.warning : colors.primary}
        />
        <View style={{ flex: 1 }}>
          <Text style={styles.label}>{uncertain ? 'Possible diagnosis' : 'Diagnosis'}</Text>
          <Text style={styles.name}>{diagnosis.name}</Text>
        </View>
        <Text style={[styles.confidence, uncertain && { color: colors.warning }]}>{percent(diagnosis.confidence)}</Text>
      </View>
      <View style={styles.meter}>
        <View
          style={[
            styles.meterFill,
            {
              width: percent(diagnosis.confidence) as `${number}%`,
              backgroundColor: uncertain ? colors.warning : colors.primary,
            },
          ]}
        />
      </View>

      {uncertain && diagnosis.alternatives.length > 0 && (
        <Text style={styles.detail}>
          Also possible: {diagnosis.alternatives.map((a) => `${a.name} (${percent(a.confidence)})`).join(', ')}
        </Text>
      )}

      {weather && (
        <View style={styles.row}>
          <Ionicons name="partly-sunny-outline" size={16} color={colors.textMuted} />
          <Text style={styles.detail}>
            {weather.condition}, {weather.temp_c}°C, {weather.humidity}% humidity
            {weather.location ? ` · ${weather.location}` : ''}
          </Text>
        </View>
      )}

      {outbreak && (
        <View style={styles.row}>
          <Ionicons name="warning-outline" size={16} color={colors.warning} />
          <Text style={[styles.detail, { color: colors.warning }]}>
            {outbreak.reports} nearby report{outbreak.reports === 1 ? '' : 's'} of this disease in the last{' '}
            {diagnosis.outbreaks!.window_days} days{outbreak.includes_demo_data ? ' (includes demo data)' : ''}
          </Text>
        </View>
      )}

      {diagnosis.nearby_places && diagnosis.nearby_places.length > 0 && (
        <View style={styles.places}>
          <Text style={styles.placesTitle}>Get help nearby</Text>
          {diagnosis.nearby_places.slice(0, 3).map((place) => (
            <Pressable key={place.maps_url} style={styles.place} onPress={() => Linking.openURL(place.maps_url)}>
              <Ionicons name="location-outline" size={16} color={colors.primary} />
              <Text style={styles.placeName} numberOfLines={1}>
                {place.name}
              </Text>
              <Text style={styles.placeMeta}>
                {place.category} · {place.distance_km} km
              </Text>
            </Pressable>
          ))}
        </View>
      )}

      {!diagnosis.location_available && (
        <Text style={styles.hint}>Share your location for weather, local outbreak alerts and nearby help.</Text>
      )}
    </View>
  );
}

const makeStyles = (colors: Colors) =>
  StyleSheet.create({
    card: {
      backgroundColor: colors.primarySoft,
      borderRadius: radius.md,
      padding: 14,
      gap: 8,
      marginTop: 2,
      marginBottom: 10,
    },
    meter: { height: 4, borderRadius: 2, backgroundColor: colors.border, overflow: 'hidden' },
    meterFill: { height: 4, borderRadius: 2 },
    cardUncertain: { backgroundColor: colors.warningSoft },
    header: { flexDirection: 'row', alignItems: 'center', gap: 10 },
    label: { fontSize: 12, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.5 },
    name: { fontSize: 17, fontWeight: '700', color: colors.text },
    confidence: { fontSize: 17, fontWeight: '700', color: colors.primary },
    row: { flexDirection: 'row', alignItems: 'flex-start', gap: 6 },
    detail: { flex: 1, fontSize: 14, color: colors.textMuted },
    places: { gap: 6, marginTop: 2 },
    placesTitle: { fontSize: 13, fontWeight: '600', color: colors.text },
    place: { flexDirection: 'row', alignItems: 'center', gap: 6 },
    placeName: { flexShrink: 1, fontSize: 14, color: colors.primaryStrong, fontWeight: '500' },
    placeMeta: { fontSize: 12, color: colors.textMuted },
    hint: { fontSize: 13, color: colors.textMuted, fontStyle: 'italic' },
  });
