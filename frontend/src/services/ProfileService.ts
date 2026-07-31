import type { ImportResponse, ProfileDetails, ProfileSummary } from '../types';

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

}
