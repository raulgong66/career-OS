import type { AnalyzeResponse, ImportResponse, ProfileDetails, ProfileSummary } from '../types';

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

    const response = await fetch(`${BASE}/profiles/import`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to import profile');
    }

    return response.json();
  }

  async getProfile(profileId: string): Promise<ProfileDetails> {
    const response = await fetch(`${BASE}/profiles/${encodeURIComponent(profileId)}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch profile');
    }

    return response.json();
  }

  async getProfiles(): Promise<ProfileSummary[]> {
    const response = await fetch(`${BASE}/profiles`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch profiles');
    }

    return response.json();
  }

  async deleteProfile(profileId: string): Promise<void> {
    const response = await fetch(`${BASE}/profiles/${encodeURIComponent(profileId)}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete profile');
    }
  }

  async analyzeProfile(profileId: string): Promise<AnalyzeResponse> {
    const response = await fetch(`${BASE}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profileId }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to analyze profile');
    }

    return response.json();
  }

  async createArtifact(profileId: string, template: string, title?: string): Promise<{ artifactId: string }> {
    const response = await fetch(`${BASE}/profiles/${encodeURIComponent(profileId)}/artifacts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ template, title }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create artifact');
    }

    return response.json();
  }

  async getTechnologyKeywords(): Promise<string[]> {
    const response = await fetch(`${BASE}/technologies`);

    if (!response.ok) {
      throw new Error('Failed to fetch technology keywords');
    }

    const data = await response.json();
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
    const response = await fetch(`${BASE}/profiles/${encodeURIComponent(profileId)}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json();
      const detail =
        typeof error?.detail === 'string' ? error.detail : error?.detail?.detail ?? 'Failed to resolve recommendation';
      throw new Error(detail);
    }

    const data = await response.json();
    return data.profile;
  }

}
