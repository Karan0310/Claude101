import axios from 'axios';
import { JobListing, ResumeProfile } from '../types';

// ── Google Jobs via SerpAPI ───────────────────────────────────────────────────

async function searchGoogleJobs(
  serpapiKey: string,
  query: string,
  location?: string,
  num = 10
): Promise<JobListing[]> {
  if (!serpapiKey) return [];
  const params: Record<string, string> = {
    engine: 'google_jobs',
    q: query,
    api_key: serpapiKey,
    num: String(num),
    hl: 'en',
  };
  if (location) params.location = location;

  const { data } = await axios.get('https://serpapi.com/search', { params });
  return (data.jobs_results || []).slice(0, num).map((item: any) => ({
    id: Math.random().toString(36).slice(2),
    title: item.title || 'Unknown Title',
    company: item.company_name || 'Unknown Company',
    location: item.location,
    description: item.description,
    salaryRange: item.detected_extensions?.salary,
    applyUrl: item.apply_options?.[0]?.link,
    source: 'google' as const,
    postedDate: item.detected_extensions?.posted_at,
  }));
}

// ── Remotive (free, no API key required) ─────────────────────────────────────

async function searchRemotiveJobs(query: string, num = 10): Promise<JobListing[]> {
  try {
    const { data } = await axios.get('https://remotive.com/api/remote-jobs', {
      params: { search: query, limit: num },
      timeout: 15000,
    });
    return (data.jobs || []).slice(0, num).map((item: any) => ({
      id: Math.random().toString(36).slice(2),
      title: item.title || 'Unknown Title',
      company: item.company_name || 'Unknown Company',
      location: item.candidate_required_location || 'Remote',
      description: (item.description || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 1500),
      salaryRange: item.salary || undefined,
      applyUrl: item.url || undefined,
      source: 'remotive' as const,
      postedDate: item.publication_date ? item.publication_date.slice(0, 10) : undefined,
    }));
  } catch {
    return [];
  }
}

// ── Demo Jobs (final fallback) ────────────────────────────────────────────────

function generateDemoJobs(profile: ResumeProfile, num: number): JobListing[] {
  const role = profile.preferredRoles[0] || 'Software Engineer';
  const skills = profile.skills.slice(0, 3).join(', ');
  const location = profile.location || 'Remote';
  const levels = ['', 'Senior ', 'Lead ', 'Staff ', 'Principal '];
  const companies = ['TechCorp', 'InnovateCo', 'DataScale', 'CloudSystems', 'NextGen', 'DigitalWave', 'FutureTech', 'CodeLabs'];

  return Array.from({ length: num }, (_, i) => ({
    id: `demo-${i}`,
    title: `${levels[i % levels.length]}${role}`,
    company: companies[i % companies.length],
    location: i % 2 === 0 ? location : 'Remote',
    description: `[DEMO - Add SerpAPI key for real jobs] We are looking for a ${role} with experience in ${skills}. Join our growing team!`,
    requirements: `3+ years experience. Skills: ${skills}`,
    salaryRange: '$90,000 - $150,000',
    applyUrl: undefined,
    source: 'demo' as const,
    postedDate: `${i + 1} day${i > 0 ? 's' : ''} ago`,
  }));
}

// ── Orchestrated Search ───────────────────────────────────────────────────────

function buildQueries(profile: ResumeProfile, extraKeywords: string[]): string[] {
  const queries: string[] = [];
  if (profile.preferredRoles[0]) queries.push(profile.preferredRoles[0]);
  if (profile.searchKeywords.length > 0) queries.push(profile.searchKeywords.slice(0, 3).join(' '));
  if (extraKeywords.length > 0) queries.push(extraKeywords.join(' '));
  return [...new Set(queries)].slice(0, 3);
}

export async function searchJobs(
  serpapiKey: string,
  profile: ResumeProfile,
  options: { location?: string; maxResults: number; remoteOk: boolean; extraKeywords?: string[] }
): Promise<JobListing[]> {
  const queries = buildQueries(profile, options.extraKeywords || []);
  const location = options.location || profile.location;
  const seen = new Set<string>();
  const all: JobListing[] = [];

  // Try SerpAPI (Google Jobs) if key provided
  for (const query of queries) {
    const searchQuery = options.remoteOk ? `${query} remote` : query;
    const jobs = await searchGoogleJobs(serpapiKey, searchQuery, location, Math.ceil(options.maxResults / queries.length));
    for (const job of jobs) {
      const key = `${job.title.toLowerCase()}|${job.company.toLowerCase()}`;
      if (!seen.has(key)) { seen.add(key); all.push(job); }
    }
  }

  // Try free Remotive API if no paid results
  if (all.length === 0) {
    for (const query of queries.slice(0, 2)) {
      const jobs = await searchRemotiveJobs(query, options.maxResults);
      for (const job of jobs) {
        const key = `${job.title.toLowerCase()}|${job.company.toLowerCase()}`;
        if (!seen.has(key)) { seen.add(key); all.push(job); }
      }
      if (all.length > 0) break;
    }
  }

  // Final fallback: demo jobs
  if (all.length === 0) return generateDemoJobs(profile, options.maxResults);
  return all.slice(0, options.maxResults);
}
