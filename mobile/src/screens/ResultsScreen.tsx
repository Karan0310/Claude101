import React, { useState } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity, Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList, JobMatch } from '../types';

const COLORS = {
  bg: '#0f172a', surface: '#1e293b', border: '#334155',
  text: '#f1f5f9', muted: '#94a3b8', primary: '#6366f1',
  success: '#22c55e', warning: '#f59e0b', danger: '#ef4444',
};

type Nav = NativeStackNavigationProp<RootStackParamList>;
type Route = RouteProp<RootStackParamList, 'Results'>;

const RATINGS = [
  { key: 'very_relevant', label: '🌟 Perfect', color: '#22c55e' },
  { key: 'relevant', label: '👍 Good', color: '#84cc16' },
  { key: 'somewhat_relevant', label: '🤔 Maybe', color: '#f59e0b' },
  { key: 'not_relevant', label: '👎 No', color: '#ef4444' },
];

function fitColor(score: number) {
  if (score >= 85) return '#22c55e';
  if (score >= 70) return '#84cc16';
  if (score >= 50) return '#f59e0b';
  return '#ef4444';
}
function fitLabel(score: number) {
  if (score >= 85) return 'Excellent';
  if (score >= 70) return 'Good Match';
  if (score >= 50) return 'Partial';
  return 'Stretch';
}

interface JobCardProps {
  match: JobMatch;
  index: number;
  rating?: string;
  onRate: (key: string) => void;
  onPress: () => void;
}

function JobCard({ match, index, rating, onRate, onPress }: JobCardProps) {
  const score = Math.round(match.fitScore);
  const color = fitColor(score);

  return (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.8}>
      <View style={styles.cardHeader}>
        <View style={styles.jobInfo}>
          <Text style={styles.jobTitle} numberOfLines={2}>{match.job.title}</Text>
          <Text style={styles.jobCompany}>{match.job.company}</Text>
          {match.job.location && (
            <Text style={styles.jobLocation}>📍 {match.job.location}</Text>
          )}
          {match.job.salaryRange && (
            <Text style={styles.salary}>💰 {match.job.salaryRange}</Text>
          )}
        </View>
        <View style={styles.scoreWrap}>
          <Text style={[styles.scoreNum, { color }]}>{score}%</Text>
          <Text style={[styles.scoreLabel, { color }]}>{fitLabel(score)}</Text>
          <View style={styles.scoreBar}>
            <View style={[styles.scoreFill, { width: `${score}%`, backgroundColor: color }]} />
          </View>
        </View>
      </View>

      {match.matchReasons[0] && (
        <View style={styles.reasonRow}>
          <Ionicons name="checkmark-circle" size={14} color={COLORS.success} />
          <Text style={styles.reasonText} numberOfLines={2}>{match.matchReasons[0]}</Text>
        </View>
      )}
      {match.gapReasons[0] && (
        <View style={styles.reasonRow}>
          <Ionicons name="warning" size={14} color={COLORS.warning} />
          <Text style={styles.reasonText} numberOfLines={2}>{match.gapReasons[0]}</Text>
        </View>
      )}

      {/* Rating */}
      <View style={styles.ratingRow}>
        {rating ? (
          <Text style={styles.ratedText}>
            ✓ Rated: {RATINGS.find(r => r.key === rating)?.label}
          </Text>
        ) : (
          <>
            <Text style={styles.rateLabel}>Rate:</Text>
            {RATINGS.map(r => (
              <TouchableOpacity key={r.key} style={styles.rateBtn} onPress={() => onRate(r.key)}>
                <Text style={styles.rateBtnText}>{r.label}</Text>
              </TouchableOpacity>
            ))}
          </>
        )}
      </View>
    </TouchableOpacity>
  );
}

export default function ResultsScreen() {
  const navigation = useNavigation<Nav>();
  const route = useRoute<Route>();
  const { matches, profile } = route.params;
  const [ratings, setRatings] = useState<Record<string, string>>({});

  function handleRate(jobId: string, rating: string) {
    setRatings(prev => ({ ...prev, [jobId]: rating }));
  }

  const avg = matches.length
    ? Math.round(matches.reduce((s, m) => s + m.fitScore, 0) / matches.length)
    : 0;

  return (
    <View style={styles.container}>
      {/* Summary Bar */}
      <View style={styles.summaryBar}>
        <View style={styles.summaryItem}>
          <Text style={styles.summaryNum}>{matches.length}</Text>
          <Text style={styles.summaryLabel}>Jobs Found</Text>
        </View>
        <View style={styles.summaryItem}>
          <Text style={[styles.summaryNum, { color: fitColor(avg) }]}>{avg}%</Text>
          <Text style={styles.summaryLabel}>Avg Fit</Text>
        </View>
        <View style={styles.summaryItem}>
          <Text style={[styles.summaryNum, { color: COLORS.success }]}>
            {matches.filter(m => m.fitScore >= 70).length}
          </Text>
          <Text style={styles.summaryLabel}>Good Matches</Text>
        </View>
        <View style={styles.summaryItem}>
          <Text style={styles.summaryNum}>{Object.keys(ratings).length}</Text>
          <Text style={styles.summaryLabel}>Rated</Text>
        </View>
      </View>

      <FlatList
        data={matches}
        keyExtractor={m => m.job.id}
        contentContainerStyle={{ padding: 16, paddingBottom: 32 }}
        renderItem={({ item, index }) => (
          <JobCard
            match={item}
            index={index}
            rating={ratings[item.job.id]}
            onRate={r => handleRate(item.job.id, r)}
            onPress={() => navigation.navigate('JobDetail', { match: item })}
          />
        )}
        ListHeaderComponent={
          profile.name ? (
            <View style={styles.profileBar}>
              <Text style={styles.profileName}>{profile.name}</Text>
              <Text style={styles.profileMeta}>
                {profile.experienceYears ? `${profile.experienceYears} yrs exp` : ''}
                {profile.location ? ` · ${profile.location}` : ''}
              </Text>
            </View>
          ) : null
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  summaryBar: {
    flexDirection: 'row', backgroundColor: COLORS.surface,
    borderBottomWidth: 1, borderBottomColor: COLORS.border,
    paddingVertical: 12,
  },
  summaryItem: { flex: 1, alignItems: 'center' },
  summaryNum: { fontSize: 20, fontWeight: '800', color: COLORS.text },
  summaryLabel: { fontSize: 10, color: COLORS.muted, marginTop: 2 },
  profileBar: {
    backgroundColor: COLORS.surface, borderRadius: 10,
    padding: 12, marginBottom: 12,
    borderWidth: 1, borderColor: COLORS.border,
  },
  profileName: { fontSize: 15, fontWeight: '700', color: COLORS.text },
  profileMeta: { fontSize: 12, color: COLORS.muted, marginTop: 2 },
  card: {
    backgroundColor: COLORS.surface, borderRadius: 12,
    padding: 14, marginBottom: 12,
    borderWidth: 1, borderColor: COLORS.border,
  },
  cardHeader: { flexDirection: 'row', gap: 12, marginBottom: 10 },
  jobInfo: { flex: 1 },
  jobTitle: { fontSize: 15, fontWeight: '700', color: COLORS.text, marginBottom: 3 },
  jobCompany: { fontSize: 13, color: COLORS.muted },
  jobLocation: { fontSize: 12, color: COLORS.muted, marginTop: 2 },
  salary: { fontSize: 12, color: COLORS.success, marginTop: 2 },
  scoreWrap: { alignItems: 'center', width: 72 },
  scoreNum: { fontSize: 24, fontWeight: '800', lineHeight: 28 },
  scoreLabel: { fontSize: 10, fontWeight: '600', marginTop: 1 },
  scoreBar: {
    width: 64, height: 4, backgroundColor: '#283548',
    borderRadius: 99, overflow: 'hidden', marginTop: 4,
  },
  scoreFill: { height: '100%', borderRadius: 99 },
  reasonRow: { flexDirection: 'row', gap: 6, marginBottom: 4, alignItems: 'flex-start' },
  reasonText: { flex: 1, fontSize: 12, color: COLORS.muted, lineHeight: 16 },
  ratingRow: {
    flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap',
    gap: 6, marginTop: 10, paddingTop: 10,
    borderTopWidth: 1, borderTopColor: COLORS.border,
  },
  rateLabel: { fontSize: 11, color: COLORS.muted },
  rateBtn: {
    backgroundColor: '#283548', borderRadius: 6, borderWidth: 1,
    borderColor: COLORS.border, paddingHorizontal: 8, paddingVertical: 4,
  },
  rateBtnText: { fontSize: 11, color: COLORS.text },
  ratedText: { fontSize: 12, color: COLORS.success },
});
