export interface ResumeProfile {
  name?: string;
  email?: string;
  location?: string;
  summary?: string;
  skills: string[];
  experienceYears?: number;
  jobTitles: string[];
  education: string[];
  searchKeywords: string[];
  preferredRoles: string[];
}

export interface JobListing {
  id: string;
  title: string;
  company: string;
  location?: string;
  description?: string;
  requirements?: string;
  salaryRange?: string;
  applyUrl?: string;
  source: 'google' | 'linkedin' | 'indeed' | 'remotive' | 'demo';
  postedDate?: string;
}

export interface JobMatch {
  job: JobListing;
  fitScore: number;
  matchReasons: string[];
  gapReasons: string[];
  recommendation: string;
  applicationTips: string[];
}

export interface AppSettings {
  anthropicApiKey: string;
  serpapiKey: string;
  rapidApiKey: string;
  adzunaAppId: string;
  adzunaAppKey: string;
  defaultLocation: string;
  maxResults: number;
  remoteOk: boolean;
}

export type RootStackParamList = {
  MainTabs: undefined;
  Results: { matches: JobMatch[]; profile: ResumeProfile };
  JobDetail: { match: JobMatch };
};

export type TabParamList = {
  Home: undefined;
  Settings: undefined;
};
