import React, { useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  TextInput, Alert, ActivityIndicator,
} from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../types';
import { loadSettings } from '../services/storageService';
import { parseResume, scoreAllJobs } from '../services/anthropicService';
import { searchJobs } from '../services/jobSearchService';

const COLORS = {
  bg: '#0f172a', surface: '#1e293b', border: '#334155',
  text: '#f1f5f9', muted: '#94a3b8', primary: '#6366f1',
  success: '#22c55e', warning: '#f59e0b',
};

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface Step { label: string; done: boolean; active: boolean }

export default function HomeScreen() {
  const navigation = useNavigation<Nav>();
  const [resumeFile, setResumeFile] = useState<{ name: string; uri: string } | null>(null);
  const [location, setLocation] = useState('');
  const [keywords, setKeywords] = useState('');
  const [loading, setLoading] = useState(false);
  const [steps, setSteps] = useState<Step[]>([]);
  const [progressMsg, setProgressMsg] = useState('');
  const [scored, setScored] = useState(0);
  const [total, setTotal] = useState(0);

  async function pickResume() {
    const result = await DocumentPicker.getDocumentAsync({
      type: ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'],
      copyToCacheDirectory: true,
    });
    if (!result.canceled && result.assets[0]) {
      setResumeFile({ name: result.assets[0].name, uri: result.assets[0].uri });
    }
  }

  function updateStep(index: number, done: boolean, active: boolean) {
    setSteps(prev => prev.map((s, i) =>
      i === index ? { ...s, done, active } : i > index ? { ...s, active: false } : s
    ));
  }

  async function handleAnalyze() {
    if (!resumeFile) { Alert.alert('No Resume', 'Please select a resume file first.'); return; }

    const settings = await loadSettings();
    if (!settings.anthropicApiKey) {
      Alert.alert('API Key Missing', 'Please add your Anthropic API key in Settings.', [
        { text: 'Go to Settings', onPress: () => navigation.navigate('MainTabs' as any) },
        { text: 'Cancel' },
      ]);
      return;
    }

    setLoading(true);
    setScored(0);
    setTotal(0);
    setSteps([
      { label: '📄 Parsing resume with Claude AI', done: false, active: true },
      { label: '🔍 Searching job boards', done: false, active: false },
      { label: '🎯 Scoring fit percentage', done: false, active: false },
      { label: '✅ Done!', done: false, active: false },
    ]);

    try {
      // Step 1: Read and parse resume
      setProgressMsg('Reading resume file...');
      const fileContent = await FileSystem.readAsStringAsync(resumeFile.uri, {
        encoding: FileSystem.EncodingType.Base64,
      });

      setProgressMsg('Parsing resume with Claude AI...');
      const resumeText = atob(fileContent);
      const profile = await parseResume(settings.anthropicApiKey, resumeText);
      updateStep(0, true, false);

      // Step 2: Search jobs
      updateStep(1, false, true);
      setProgressMsg('Searching job boards...');
      const extraKeywords = keywords.split(',').map(k => k.trim()).filter(Boolean);
      const jobs = await searchJobs(settings.serpapiKey, profile, {
        location: location || settings.defaultLocation || undefined,
        maxResults: settings.maxResults,
        remoteOk: settings.remoteOk,
        extraKeywords,
      });
      updateStep(1, true, false);

      // Step 3: Score jobs
      updateStep(2, false, true);
      setTotal(jobs.length);
      setProgressMsg(`Scoring ${jobs.length} jobs...`);
      const matches = await scoreAllJobs(
        settings.anthropicApiKey, profile, jobs,
        (done, t) => { setScored(done); setProgressMsg(`Scored ${done}/${t} jobs...`); }
      );
      updateStep(2, true, false);
      updateStep(3, true, true);

      setProgressMsg('Done! Redirecting...');
      setTimeout(() => {
        setLoading(false);
        navigation.navigate('Results', { matches, profile });
      }, 600);

    } catch (err: any) {
      setLoading(false);
      const msg = err?.response?.data?.error?.message || err.message || 'Unknown error';
      Alert.alert('Error', msg);
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Resume-Job Matcher</Text>
        <Text style={styles.subtitle}>Upload your resume — AI finds your best-fit jobs</Text>
      </View>

      {/* Upload Card */}
      <View style={styles.card}>
        <TouchableOpacity style={styles.uploadZone} onPress={pickResume} disabled={loading}>
          <Ionicons name={resumeFile ? 'document-text' : 'cloud-upload'} size={40} color={COLORS.primary} />
          {resumeFile ? (
            <>
              <Text style={styles.uploadTitle}>{resumeFile.name}</Text>
              <Text style={styles.uploadSub}>Tap to change</Text>
            </>
          ) : (
            <>
              <Text style={styles.uploadTitle}>Tap to upload resume</Text>
              <Text style={styles.uploadSub}>PDF, DOCX, or TXT</Text>
            </>
          )}
        </TouchableOpacity>
      </View>

      {/* Options */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Search Options</Text>
        <View style={styles.field}>
          <Text style={styles.label}>Location (optional)</Text>
          <TextInput
            style={styles.input}
            value={location}
            onChangeText={setLocation}
            placeholder="e.g. New York, Remote"
            placeholderTextColor={COLORS.muted}
          />
        </View>
        <View style={styles.field}>
          <Text style={styles.label}>Extra keywords (optional)</Text>
          <TextInput
            style={styles.input}
            value={keywords}
            onChangeText={setKeywords}
            placeholder="e.g. startup, fintech, Python"
            placeholderTextColor={COLORS.muted}
          />
        </View>
      </View>

      {/* Progress */}
      {loading && (
        <View style={styles.card}>
          <Text style={styles.progressMsg}>{progressMsg}</Text>
          {total > 0 && (
            <View style={styles.progressBarWrap}>
              <View style={[styles.progressBarFill, { width: `${(scored / total) * 100}%` }]} />
            </View>
          )}
          <View style={styles.stepList}>
            {steps.map((step, i) => (
              <View key={i} style={styles.stepRow}>
                {step.done
                  ? <Ionicons name="checkmark-circle" size={16} color={COLORS.success} />
                  : step.active
                  ? <ActivityIndicator size={14} color={COLORS.primary} />
                  : <View style={styles.stepDot} />
                }
                <Text style={[styles.stepLabel, step.active && styles.stepLabelActive, step.done && styles.stepLabelDone]}>
                  {step.label}
                </Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* Analyze Button */}
      <TouchableOpacity
        style={[styles.analyzeBtn, (!resumeFile || loading) && styles.analyzeBtnDisabled]}
        onPress={handleAnalyze}
        disabled={!resumeFile || loading}
      >
        {loading
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.analyzeBtnText}>Analyze &amp; Find Jobs</Text>
        }
      </TouchableOpacity>

      {/* How it works */}
      <View style={styles.howItWorks}>
        <Text style={styles.cardTitle}>How It Works</Text>
        {[
          ['🤖', 'Claude AI reads your resume and extracts skills, experience, and career profile'],
          ['🔍', 'Searches Google Jobs, LinkedIn, and Indeed using smart queries from your profile'],
          ['🎯', 'Each job gets a fit score (0-100%) with match reasons and skill gaps'],
          ['📊', 'Rate results to trigger AI evaluation of recommendation quality'],
        ].map(([icon, text], i) => (
          <View key={i} style={styles.howRow}>
            <Text style={styles.howIcon}>{icon}</Text>
            <Text style={styles.howText}>{text}</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  content: { padding: 16, paddingBottom: 40 },
  header: { alignItems: 'center', paddingVertical: 24 },
  title: {
    fontSize: 26, fontWeight: '800', color: COLORS.text,
    textAlign: 'center', marginBottom: 6,
  },
  subtitle: { fontSize: 14, color: COLORS.muted, textAlign: 'center' },
  card: {
    backgroundColor: COLORS.surface, borderRadius: 12,
    padding: 16, marginBottom: 16,
    borderWidth: 1, borderColor: COLORS.border,
  },
  cardTitle: { fontSize: 15, fontWeight: '700', color: COLORS.text, marginBottom: 12 },
  uploadZone: {
    borderWidth: 2, borderColor: COLORS.border, borderStyle: 'dashed',
    borderRadius: 12, padding: 32, alignItems: 'center', gap: 8,
  },
  uploadTitle: { fontSize: 15, fontWeight: '600', color: COLORS.text },
  uploadSub: { fontSize: 12, color: COLORS.muted },
  field: { marginBottom: 12 },
  label: { fontSize: 12, fontWeight: '600', color: COLORS.muted, marginBottom: 6 },
  input: {
    backgroundColor: '#283548', borderWidth: 1, borderColor: COLORS.border,
    borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10,
    color: COLORS.text, fontSize: 14,
  },
  progressMsg: { fontSize: 13, color: COLORS.muted, marginBottom: 10, textAlign: 'center' },
  progressBarWrap: {
    height: 6, backgroundColor: '#283548', borderRadius: 99,
    overflow: 'hidden', marginBottom: 12,
  },
  progressBarFill: { height: '100%', backgroundColor: COLORS.primary, borderRadius: 99 },
  stepList: { gap: 8 },
  stepRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  stepDot: { width: 14, height: 14, borderRadius: 7, borderWidth: 1, borderColor: COLORS.border },
  stepLabel: { fontSize: 13, color: COLORS.muted },
  stepLabelActive: { color: COLORS.text, fontWeight: '600' },
  stepLabelDone: { color: COLORS.success },
  analyzeBtn: {
    backgroundColor: COLORS.primary, borderRadius: 12,
    paddingVertical: 16, alignItems: 'center', marginBottom: 16,
  },
  analyzeBtnDisabled: { opacity: 0.5 },
  analyzeBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  howItWorks: {
    backgroundColor: COLORS.surface, borderRadius: 12,
    padding: 16, borderWidth: 1, borderColor: COLORS.border,
  },
  howRow: { flexDirection: 'row', gap: 10, marginBottom: 10, alignItems: 'flex-start' },
  howIcon: { fontSize: 18, width: 24 },
  howText: { flex: 1, fontSize: 13, color: COLORS.muted, lineHeight: 18 },
});
