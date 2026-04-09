import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity, Linking,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRoute, RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../types';

const COLORS = {
  bg: '#0f172a', surface: '#1e293b', border: '#334155',
  text: '#f1f5f9', muted: '#94a3b8', primary: '#6366f1',
  success: '#22c55e', warning: '#f59e0b', danger: '#ef4444',
};

type Route = RouteProp<RootStackParamList, 'JobDetail'>;

function fitColor(score: number) {
  if (score >= 85) return '#22c55e';
  if (score >= 70) return '#84cc16';
  if (score >= 50) return '#f59e0b';
  return '#ef4444';
}

export default function JobDetailScreen() {
  const { match } = useRoute<Route>().params;
  const { job, fitScore, matchReasons, gapReasons, recommendation, applicationTips } = match;
  const score = Math.round(fitScore);
  const color = fitColor(score);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>{job.title}</Text>
        <Text style={styles.company}>{job.company}</Text>
        <View style={styles.metaRow}>
          {job.location && <Text style={styles.meta}>📍 {job.location}</Text>}
          {job.postedDate && <Text style={styles.meta}>🕐 {job.postedDate}</Text>}
          {job.source && <Text style={styles.sourceBadge}>{job.source.toUpperCase()}</Text>}
        </View>
        {job.salaryRange && <Text style={styles.salary}>💰 {job.salaryRange}</Text>}
      </View>

      {/* Fit Score */}
      <View style={[styles.card, styles.scoreCard]}>
        <View style={styles.scoreCircle}>
          <Text style={[styles.scoreBig, { color }]}>{score}%</Text>
          <Text style={[styles.scoreSubtitle, { color }]}>
            {score >= 85 ? 'Excellent Match' : score >= 70 ? 'Good Match' : score >= 50 ? 'Partial Match' : 'Stretch Role'}
          </Text>
        </View>
        <View style={styles.scoreBarWrap}>
          <View style={styles.scoreBarBg}>
            <View style={[styles.scoreBarFill, { width: `${score}%`, backgroundColor: color }]} />
          </View>
        </View>
        {recommendation ? (
          <Text style={styles.recommendation}>{recommendation}</Text>
        ) : null}
      </View>

      {/* Match Reasons */}
      {matchReasons.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>✅ Why You Match</Text>
          {matchReasons.map((r, i) => (
            <View key={i} style={styles.listRow}>
              <Ionicons name="checkmark-circle" size={15} color={COLORS.success} />
              <Text style={styles.listText}>{r}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Gaps */}
      {gapReasons.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>⚠️ Gaps to Address</Text>
          {gapReasons.map((g, i) => (
            <View key={i} style={styles.listRow}>
              <Ionicons name="warning" size={15} color={COLORS.warning} />
              <Text style={styles.listText}>{g}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Application Tips */}
      {applicationTips.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>💡 Application Tips</Text>
          {applicationTips.map((t, i) => (
            <View key={i} style={styles.listRow}>
              <Text style={styles.tipNum}>{i + 1}</Text>
              <Text style={styles.listText}>{t}</Text>
            </View>
          ))}
        </View>
      )}

      {/* Description */}
      {job.description && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>📋 Job Description</Text>
          <Text style={styles.description}>{job.description}</Text>
        </View>
      )}

      {/* Apply Button */}
      {job.applyUrl ? (
        <TouchableOpacity
          style={styles.applyBtn}
          onPress={() => Linking.openURL(job.applyUrl!)}
        >
          <Text style={styles.applyBtnText}>Apply Now</Text>
          <Ionicons name="arrow-forward" size={18} color="#fff" />
        </TouchableOpacity>
      ) : (
        <View style={styles.noApplyNote}>
          <Text style={styles.noApplyText}>
            {job.source === 'demo'
              ? 'Add a SerpAPI key in Settings for real job listings with apply links.'
              : job.source === 'remotive'
              ? 'Visit remotive.com to find and apply to this position.'
              : 'No direct apply link available — search for this role on the company website.'}
          </Text>
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  content: { padding: 16, paddingBottom: 40 },
  header: {
    backgroundColor: COLORS.surface, borderRadius: 12,
    padding: 16, marginBottom: 12,
    borderWidth: 1, borderColor: COLORS.border,
  },
  title: { fontSize: 20, fontWeight: '800', color: COLORS.text, marginBottom: 4 },
  company: { fontSize: 15, color: COLORS.primary, marginBottom: 8 },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, alignItems: 'center' },
  meta: { fontSize: 12, color: COLORS.muted },
  sourceBadge: {
    fontSize: 10, color: COLORS.muted, backgroundColor: '#283548',
    borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2,
    borderWidth: 1, borderColor: COLORS.border,
  },
  salary: { fontSize: 13, color: COLORS.success, marginTop: 6 },
  card: {
    backgroundColor: COLORS.surface, borderRadius: 12,
    padding: 16, marginBottom: 12,
    borderWidth: 1, borderColor: COLORS.border,
  },
  scoreCard: { alignItems: 'center' },
  scoreCircle: { alignItems: 'center', marginBottom: 12 },
  scoreBig: { fontSize: 52, fontWeight: '900', lineHeight: 56 },
  scoreSubtitle: { fontSize: 14, fontWeight: '700', marginTop: 2 },
  scoreBarWrap: { width: '100%', marginBottom: 12 },
  scoreBarBg: { height: 8, backgroundColor: '#283548', borderRadius: 99, overflow: 'hidden' },
  scoreBarFill: { height: '100%', borderRadius: 99 },
  recommendation: {
    fontSize: 13, color: COLORS.muted, textAlign: 'center',
    fontStyle: 'italic', lineHeight: 18,
  },
  sectionTitle: { fontSize: 14, fontWeight: '700', color: COLORS.text, marginBottom: 10 },
  listRow: { flexDirection: 'row', gap: 8, marginBottom: 8, alignItems: 'flex-start' },
  listText: { flex: 1, fontSize: 13, color: COLORS.muted, lineHeight: 18 },
  tipNum: {
    width: 20, height: 20, borderRadius: 10, backgroundColor: COLORS.primary,
    color: '#fff', fontSize: 11, fontWeight: '700',
    textAlign: 'center', lineHeight: 20,
  },
  description: { fontSize: 13, color: COLORS.muted, lineHeight: 20 },
  applyBtn: {
    backgroundColor: COLORS.primary, borderRadius: 12,
    paddingVertical: 16, flexDirection: 'row',
    alignItems: 'center', justifyContent: 'center', gap: 8,
  },
  applyBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  noApplyNote: {
    backgroundColor: COLORS.surface, borderRadius: 10,
    padding: 14, borderWidth: 1, borderColor: COLORS.border,
  },
  noApplyText: { fontSize: 13, color: COLORS.muted, textAlign: 'center', lineHeight: 18 },
});
