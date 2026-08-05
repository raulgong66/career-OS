import type {
  AnalyzeResponse,
  ImportResponse,
  ProfileDetails,
  ProfileSummary,
  QualityReport,
  UnifiedRecommendation,
} from '../types';
import { fetchJson } from './http';

const BASE = '';

export class ProfileService {
  private static instance: ProfileService;

  private constructor() {}

  static getInstance(): ProfileService {
    if (!ProfileService.instance) {
      ProfileService.instance = new ProfileService();
    }
    return ProfileService.instance;
  }

  async uploadProfile(file: File): Promise<ImportResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return fetchJson<ImportResponse>(`${BASE}/profiles/import`, {
      method: 'POST',
      body: formData,
    }, 'Failed to import profile');
  }

  async getProfile(profileId: string): Promise<ProfileDetails> {
    return fetchJson<ProfileDetails>(
      `${BASE}/profiles/${encodeURIComponent(profileId)}`,
      undefined,
      'Failed to fetch profile',
    );
  }

  async getCanonicalProfile(profileId: string): Promise<Record<string, unknown>> {
    return fetchJson<Record<string, unknown>>(
      `${BASE}/profiles/${encodeURIComponent(profileId)}/canonical`,
      undefined,
      'Failed to fetch canonical profile',
    );
  }

  async getProfiles(): Promise<ProfileSummary[]> {
    return fetchJson<ProfileSummary[]>(`${BASE}/profiles`, undefined, 'Failed to fetch profiles');
  }

  async deleteProfile(profileId: string): Promise<void> {
    await fetchJson<unknown>(
      `${BASE}/profiles/${encodeURIComponent(profileId)}`,
      { method: 'DELETE' },
      'Failed to delete profile',
    );
  }

  async analyzeProfile(profileId: string): Promise<AnalyzeResponse> {
    return fetchJson<AnalyzeResponse>(`${BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profileId }),
    }, 'Failed to analyze profile');
  }

  async getQualityReport(profileId: string): Promise<QualityReport> {
    return fetchJson<QualityReport>(
      `${BASE}/profiles/${encodeURIComponent(profileId)}/quality-report`,
      undefined,
      'Failed to fetch quality report',
    );
  }

  async getImprovementQueue(
    profileId: string,
    filters?: { priority?: string; resolutionType?: string },
  ): Promise<UnifiedRecommendation[]> {
    const params = new URLSearchParams();
    if (filters?.priority) params.set('priority', filters.priority);
    if (filters?.resolutionType) params.set('resolution_type', filters.resolutionType);
    const query = params.toString();
    return fetchJson<UnifiedRecommendation[]>(
      `${BASE}/profiles/${encodeURIComponent(profileId)}/improvement-queue${query ? `?${query}` : ''}`,
      undefined,
      'Failed to fetch improvement queue',
    );
  }

  async createArtifact(profileId: string, template: string, title?: string): Promise<{ artifactId: string }> {
    return fetchJson<{ artifactId: string }>(
      `${BASE}/profiles/${encodeURIComponent(profileId)}/artifacts`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template, title }),
      },
      'Failed to create artifact',
    );
  }

  async getTechnologyKeywords(): Promise<string[]> {
    const data = await fetchJson<{ keywords?: string[] }>(
      `${BASE}/technologies`,
      undefined,
      'Failed to fetch technology keywords',
    );
    return data.keywords ?? [];
  }

  async resolveRecommendation(
    profileId: string,
    request: {
      triggeredRule: string;
      elementId: string;
      skillIds: string[];
      experienceIds: string[];
      technologies: string[];
      achievementStatement: string;
    },
  ): Promise<ProfileDetails> {
    const data = await fetchJson<{ profile: ProfileDetails }>(
      `${BASE}/profiles/${encodeURIComponent(profileId)}/resolve`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      },
      'Failed to resolve recommendation',
    );
    return data.profile;
  }

}
