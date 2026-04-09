import React, { useEffect, useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, ScrollView,
  TouchableOpacity, Alert, Switch, ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { AppSettings } from '../types';
import { loadSettings, saveSettings } from '../services/storageService';

const COLORS = {
  bg: '#0f172a', surface: '#1e293b', border: '#334155',
  text: '#f1f5f9', muted: '#94a3b8', primary: '#6366f1',
  success: '#22c55e', danger: '#ef4444',
};

interface FieldProps {
  label: string;
  value: string;
  placeholder: string;
  onChangeText: (v: string) => void;
  secure?: boolean;
  hint?: string;
}

function Field({ label, value, placeholder, onChangeText, secure, hint }: FieldProps) {
  const [show, setShow] = useState(false);
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.inputRow}>
        <TextInput
          style={[styles.input, { flex: 1 }]}
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={COLORS.muted}
          secureTextEntry={secure && !show}
          autoCapitalize="none"
          autoCorrect={false}
        />
        {secure && (
          <TouchableOpacity onPress={() => setShow(s => !s)} style={styles.eyeBtn}>
            <Ionicons name={show ? 'eye-off' : 'eye'} size={18} color={COLORS.muted} />
          </TouchableOpacity>
        )}
      </View>
      {hint && <Text style={styles.hint}>{hint}</Text>}
    </View>
  );
}

export default function SettingsScreen() {
  const [settings, setSettings] = useState<AppSettings>({
    anthropicApiKey: '', serpapiKey: '', rapidApiKey: '',
    defaultLocation: '', maxResults: 10, remoteOk: true,
  });
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    loadSettings().then(s => { setSettings(s); setLoaded(true); });
  }, []);

  const set = (key: keyof AppSettings) => (value: any) =>
    setSettings(prev => ({ ...prev, [key]: value }));

  async function handleSave() {
    if (!settings.anthropicApiKey.trim()) {
      Alert.alert('Required', 'Anthropic API key is required to use the app.');
      return;
    }
    setSaving(true);
    await saveSettings(settings);
    setSaving(false);
    Alert.alert('Saved', 'Settings saved securely on your device.');
  }

  if (!loaded) return <View style={styles.container}><ActivityIndicator color={COLORS.primary} /></View>;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>🤖 AI Configuration</Text>
        <Field
          label="Anthropic API Key *"
          value={settings.anthropicApiKey}
          placeholder="sk-ant-api03-..."
          onChangeText={set('anthropicApiKey')}
          secure
          hint="Required. Get yours at console.anthropic.com"
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>🔍 Job Search APIs</Text>
        <Text style={styles.sectionNote}>Optional. Without these, demo job listings are used.</Text>
        <Field
          label="SerpAPI Key"
          value={settings.serpapiKey}
          placeholder="Your SerpAPI key"
          onChangeText={set('serpapiKey')}
          secure
          hint="Google Jobs + Indeed. Free 100 searches/month at serpapi.com"
        />
        <Field
          label="RapidAPI Key"
          value={settings.rapidApiKey}
          placeholder="Your RapidAPI key"
          onChangeText={set('rapidApiKey')}
          secure
          hint="LinkedIn Jobs. Free tier at rapidapi.com"
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>⚙️ Search Preferences</Text>
        <Field
          label="Default Location"
          value={settings.defaultLocation}
          placeholder="e.g. New York, Remote"
          onChangeText={set('defaultLocation')}
        />
        <View style={styles.field}>
          <Text style={styles.label}>Max Results: {settings.maxResults}</Text>
          <View style={styles.stepper}>
            {[5, 10, 15, 20].map(n => (
              <TouchableOpacity
                key={n}
                style={[styles.stepBtn, settings.maxResults === n && styles.stepBtnActive]}
                onPress={() => set('maxResults')(n)}
              >
                <Text style={[styles.stepBtnText, settings.maxResults === n && styles.stepBtnTextActive]}>
                  {n}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
        <View style={[styles.field, styles.row]}>
          <View>
            <Text style={styles.label}>Include Remote Jobs</Text>
            <Text style={styles.hint}>Search for remote positions</Text>
          </View>
          <Switch
            value={settings.remoteOk}
            onValueChange={set('remoteOk')}
            trackColor={{ false: COLORS.border, true: COLORS.primary }}
            thumbColor="#fff"
          />
        </View>
      </View>

      <TouchableOpacity style={styles.saveBtn} onPress={handleSave} disabled={saving}>
        {saving
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.saveBtnText}>Save Settings</Text>
        }
      </TouchableOpacity>

      <Text style={styles.secureNote}>
        🔒 API keys are stored encrypted on your device using iOS Keychain / Android Keystore.
        They are never sent to any server other than the respective API providers.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  content: { padding: 16, paddingBottom: 40 },
  section: {
    backgroundColor: COLORS.surface, borderRadius: 12,
    padding: 16, marginBottom: 16,
    borderWidth: 1, borderColor: COLORS.border,
  },
  sectionTitle: { fontSize: 15, fontWeight: '700', color: COLORS.text, marginBottom: 4 },
  sectionNote: { fontSize: 12, color: COLORS.muted, marginBottom: 12 },
  field: { marginBottom: 16 },
  label: { fontSize: 13, fontWeight: '600', color: COLORS.muted, marginBottom: 6 },
  inputRow: { flexDirection: 'row', alignItems: 'center' },
  input: {
    backgroundColor: '#283548', borderWidth: 1, borderColor: COLORS.border,
    borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10,
    color: COLORS.text, fontSize: 14,
  },
  eyeBtn: { position: 'absolute', right: 10 },
  hint: { fontSize: 11, color: COLORS.muted, marginTop: 4 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  stepper: { flexDirection: 'row', gap: 8, marginTop: 4 },
  stepBtn: {
    flex: 1, paddingVertical: 8, borderRadius: 8,
    borderWidth: 1, borderColor: COLORS.border, alignItems: 'center',
  },
  stepBtnActive: { backgroundColor: COLORS.primary, borderColor: COLORS.primary },
  stepBtnText: { color: COLORS.muted, fontWeight: '600' },
  stepBtnTextActive: { color: '#fff' },
  saveBtn: {
    backgroundColor: COLORS.primary, borderRadius: 10,
    paddingVertical: 14, alignItems: 'center', marginBottom: 16,
  },
  saveBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  secureNote: {
    fontSize: 11, color: COLORS.muted, textAlign: 'center',
    lineHeight: 16, paddingHorizontal: 8,
  },
});
