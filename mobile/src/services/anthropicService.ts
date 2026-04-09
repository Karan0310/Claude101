import axios from 'axios';
import { ResumeProfile, JobListing, JobMatch } from '../types';

const ANTHROPIC_URL = 'https://api.anthropic.com/v1/messages';
const MODEL = 'claude-sonnet-4-6';

function makeHeaders(apiKey: string) {
  return {
    'x-api-key': apiKey,
    'anthropic-version': '2023-06-01',
    'content-type': 'application/json',
  };
}

async function callClaude(apiKey: string, system: string, user: string): Promise<string> {
  const response = await axios.post(
    ANTHROPIC_URL,
    { model: MODEL, max_tokens: 2048, system, messages: [{ role: 'user', content: user }] },
    { headers: makeHeaders(apiKey) }
  );
  return response.data.content[0].text.trim();
}

function stripFences(text: string): string {
  if (text.startsWith('```')) {
    const lines = text.split('\n');
    return lines.slice(1, -1).join('\n');
  }
  return text;
}

// ── Resume Parsing ────────────────────────────────────────────────────────────

export async function parseResume(apiKey: string, resumeText: string): Promise<ResumeProfile> {
  const system = 'You are an expert resume analyzer. Extract structured information accurately. Respond with valid JSON only, no markdown.';
  const user = `Analyze this resume and return a JSON object with exactly these fields:
{
  "name": "full name or null",
  "email": "email or null",
  "location": "city/state or null",
  "summary": "2-3 sentence professional summary or null",
  "skills": ["skill1", "skill2"],
  "experienceYears": <number or null>,
  "jobTitles": ["title1"],
  "education": ["Degree - School - Year"],
  "searchKeywords": ["10-15 job search keywords"],
  "preferredRoles": ["5-8 best-fit job roles"]
}

Resume:
${resumeText.slice(0, 12000)}`;

  const raw = stripFences(await callClaude(apiKey, system, user));
  const parsed = JSON.parse(raw);
  return {
    name: parsed.name,
    email: parsed.email,
    location: parsed.location,
    summary: parsed.summary,
    skills: parsed.skills || [],
    experienceYears: parsed.experienceYears,
    jobTitles: parsed.jobTitles || [],
    education: parsed.education || [],
    searchKeywords: parsed.searchKeywords || [],
    preferredRoles: parsed.preferredRoles || [],
  };
}

// ── Job Scoring ───────────────────────────────────────────────────────────────

export async function scoreJobMatch(
  apiKey: string,
  profile: ResumeProfile,
  job: JobListing
): Promise<JobMatch> {
  const system = 'You are an expert recruiter. Evaluate candidate-job fit objectively. Respond with valid JSON only, no markdown.';
  const user = `Evaluate this candidate's fit for the job and return JSON:

CANDIDATE:
- Skills: ${profile.skills.slice(0, 20).join(', ')}
- Experience: ${profile.experienceYears ?? '?'} years
- Titles: ${profile.jobTitles.slice(0, 5).join(', ')}
- Education: ${profile.education.slice(0, 2).join(', ')}

JOB:
- Title: ${job.title}
- Company: ${job.company}
- Location: ${job.location ?? 'Not specified'}
- Description: ${(job.description ?? '').slice(0, 1500)}

Return:
{
  "fitScore": <0-100>,
  "matchReasons": ["reason1", "reason2", "reason3"],
  "gapReasons": ["gap1", "gap2"],
  "recommendation": "1-2 sentence recommendation",
  "applicationTips": ["tip1", "tip2", "tip3"]
}`;

  const raw = stripFences(await callClaude(apiKey, system, user));
  const r = JSON.parse(raw);
  return {
    job,
    fitScore: Math.min(100, Math.max(0, Number(r.fitScore ?? 50))),
    matchReasons: r.matchReasons || [],
    gapReasons: r.gapReasons || [],
    recommendation: r.recommendation || '',
    applicationTips: r.applicationTips || [],
  };
}

export async function scoreAllJobs(
  apiKey: string,
  profile: ResumeProfile,
  jobs: JobListing[],
  onProgress?: (done: number, total: number) => void
): Promise<JobMatch[]> {
  const results: JobMatch[] = [];
  for (let i = 0; i < jobs.length; i++) {
    const match = await scoreJobMatch(apiKey, profile, jobs[i]);
    results.push(match);
    onProgress?.(i + 1, jobs.length);
  }
  return results.sort((a, b) => b.fitScore - a.fitScore);
}
