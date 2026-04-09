import axios from 'axios';
import { JobListing, ResumeProfile } from '../types';

// ── Adzuna (free API key, millions of real jobs) ──────────────────────────────

async function searchAdzunaJobs(
  appId: string,
  appKey: string,
  query: string,
  location?: string,
  num = 10
): Promise<JobListing[]> {
  if (!appId || !appKey) return [];
  const params: Record<string, string> = {
    app_id: appId,
    app_key: appKey,
    results_per_page: String(Math.min(num, 50)),
    what: query,
    'content-type': 'application/json',
  };
  if (location) params.where = location;
  try {
    const { data } = await axios.get('https://api.adzuna.com/v1/api/jobs/us/search/1', { params, timeout: 20000 });
    return (data.results || []).slice(0, num).map((item: any) => {
      const salMin = item.salary_min, salMax = item.salary_max;
      const salary = salMin && salMax ? `$${Math.round(salMin).toLocaleString()} – $${Math.round(salMax).toLocaleString()}`
        : salMin ? `$${Math.round(salMin).toLocaleString()}+` : undefined;
      return {
        id: Math.random().toString(36).slice(2),
        title: item.title || 'Unknown Title',
        company: item.company?.display_name || 'Unknown Company',
        location: item.location?.display_name,
        description: item.description,
        salaryRange: salary,
        applyUrl: item.redirect_url,
        source: 'google' as const,
        postedDate: item.created?.slice(0, 10),
      };
    });
  } catch { return []; }
}

// ── Arbeitnow (free, no key, EU + remote tech jobs) ───────────────────────────

async function searchArbeitnowJobs(query: string, num = 10): Promise<JobListing[]> {
  try {
    const { data } = await axios.get('https://www.arbeitnow.com/api/job-board-api', {
      params: { search: query },
      timeout: 15000,
    });
    return (data.data || []).slice(0, num).map((item: any) => ({
      id: Math.random().toString(36).slice(2),
      title: item.title || 'Unknown Title',
      company: item.company_name || 'Unknown Company',
      location: item.location || (item.remote ? 'Remote' : undefined),
      description: (item.description || '').slice(0, 1500),
      applyUrl: item.url,
      source: 'remotive' as const,
      postedDate: String(item.published_at || '').slice(0, 10) || undefined,
    }));
  } catch { return []; }
}

// ── Himalayas (free, no key, remote tech jobs) ────────────────────────────────

async function searchHimalayasJobs(query: string, num = 10): Promise<JobListing[]> {
  try {
    const { data } = await axios.get('https://himalayas.app/jobs/api', {
      params: { q: query, limit: num },
      timeout: 15000,
    });
    return (data.jobs || []).slice(0, num).map((item: any) => ({
      id: Math.random().toString(36).slice(2),
      title: item.title || 'Unknown Title',
      company: item.companyName || 'Unknown Company',
      location: item.locationRestrictions || 'Remote',
      description: (item.description || '').slice(0, 1500),
      salaryRange: item.salary,
      applyUrl: item.applicationLink || item.url,
      source: 'remotive' as const,
      postedDate: item.publishedAt?.slice(0, 10),
    }));
  } catch { return []; }
}

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
  options: {
    location?: string; maxResults: number; remoteOk: boolean;
    extraKeywords?: string[];
    adzunaAppId?: string; adzunaAppKey?: string;
  }
): Promise<JobListing[]> {
  const queries = buildQueries(profile, options.extraKeywords || []);
  const primaryQuery = queries[0] || 'software engineer';
  const location = options.location || profile.location;
  const seen = new Set<string>();
  const all: JobListing[] = [];

  function addUnique(jobs: JobListing[]) {
    for (const job of jobs) {
      const key = `${job.title.toLowerCase()}|${job.company.toLowerCase()}`;
      if (!seen.has(key)) { seen.add(key); all.push(job); }
    }
  }

  const perQuery = Math.ceil(options.maxResults / Math.max(queries.length, 1));

  // Tier 1: paid SerpAPI (Google Jobs)
  for (const query of queries) {
    const q = options.remoteOk ? `${query} remote` : query;
    addUnique(await searchGoogleJobs(serpapiKey, q, location, perQuery));
  }

  // Tier 2: Adzuna (free key, broad global coverage)
  if (options.adzunaAppId && options.adzunaAppKey) {
    for (const query of queries.slice(0, 2)) {
      addUnique(await searchAdzunaJobs(options.adzunaAppId, options.adzunaAppKey, query, location, perQuery));
    }
  }

  // Tier 3: free no-key sources (always run to enrich results)
  addUnique(await searchRemotiveJobs(primaryQuery, options.maxResults));
  addUnique(await searchArbeitnowJobs(primaryQuery, options.maxResults));
  addUnique(await searchHimalayasJobs(primaryQuery, options.maxResults));

  if (all.length === 0) return generateDemoJobs(profile, options.maxResults);
  return all.slice(0, options.maxResults);
}
