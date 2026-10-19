import { Image } from 'expo-image';
import { Link, type Href } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { KeyboardAwareScrollView } from 'react-native-keyboard-controller';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useTheme, useThemedStyles } from '@/lib/theme';
import { radius, type Colors } from '@/theme';

type Field = { key: string; label: string; secure?: boolean; email?: boolean };

type Props = {
  title: string;
  subtitle: string;
  fields: Field[];
  submitLabel: string;
  onSubmit: (values: Record<string, string>) => Promise<void>;
  footerText: string;
  footerLink: { href: Href; label: string };
};

export function AuthForm({ title, subtitle, fields, submitLabel, onSubmit, footerText, footerLink }: Props) {
  const { colors } = useTheme();
  const styles = useThemedStyles(makeStyles);
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError(null);
    setBusy(true);
    try {
      await onSubmit(values);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAwareScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
        bottomOffset={24}
      >
        <Image source={require('../../assets/logo.png')} style={styles.logo} contentFit="contain" />
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.subtitle}>{subtitle}</Text>

        {fields.map((field) => (
          <View key={field.key} style={styles.field}>
            <Text style={styles.label}>{field.label}</Text>
            <TextInput
              style={styles.input}
              value={values[field.key] ?? ''}
              onChangeText={(text) => setValues((v) => ({ ...v, [field.key]: text }))}
              secureTextEntry={field.secure}
              autoCapitalize={field.email || field.secure ? 'none' : 'words'}
              autoComplete={field.email ? 'email' : field.secure ? 'password' : 'name'}
              keyboardType={field.email ? 'email-address' : 'default'}
              placeholderTextColor={colors.textMuted}
              selectionColor={colors.primary}
              onSubmitEditing={field === fields[fields.length - 1] ? submit : undefined}
            />
          </View>
        ))}

        {error && <Text style={styles.error}>{error}</Text>}

        <Pressable style={[styles.button, busy && { opacity: 0.7 }]} onPress={submit} disabled={busy}>
          {busy ? <ActivityIndicator color={colors.onPrimary} /> : <Text style={styles.buttonText}>{submitLabel}</Text>}
        </Pressable>

        <Text style={styles.footer}>
          {footerText}{' '}
          <Link href={footerLink.href} replace style={styles.link}>
            {footerLink.label}
          </Link>
        </Text>
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}

const makeStyles = (colors: Colors) =>
  StyleSheet.create({
    safe: { flex: 1, backgroundColor: colors.background },
    container: { flexGrow: 1, justifyContent: 'center', padding: 24 },
    logo: { width: 72, height: 72, alignSelf: 'center', marginBottom: 16 },
    title: { fontSize: 26, fontWeight: '700', color: colors.text, textAlign: 'center' },
    subtitle: { fontSize: 15, color: colors.textMuted, textAlign: 'center', marginTop: 6, marginBottom: 28 },
    field: { marginBottom: 14 },
    label: { fontSize: 14, fontWeight: '600', color: colors.text, marginBottom: 6 },
    input: {
      backgroundColor: colors.surface,
      borderWidth: 1,
      borderColor: colors.border,
      borderRadius: radius.sm,
      paddingHorizontal: 14,
      paddingVertical: 12,
      fontSize: 16,
      color: colors.text,
    },
    error: { color: colors.danger, marginBottom: 12, textAlign: 'center' },
    button: {
      backgroundColor: colors.primary,
      borderRadius: radius.sm,
      paddingVertical: 14,
      alignItems: 'center',
      marginTop: 8,
    },
    buttonText: { color: colors.onPrimary, fontSize: 16, fontWeight: '600' },
    footer: { textAlign: 'center', marginTop: 20, color: colors.textMuted },
    link: { color: colors.primary, fontWeight: '600' },
  });
