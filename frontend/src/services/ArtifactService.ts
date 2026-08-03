import type { ArtifactTemplate, ProfileDetails } from '../types';

const BASE = '';

function errorDetail(body: unknown, fallback: string): string {
  if (body && typeof body === 'object') {
    const record = body as Record<string, unknown>;
    if (typeof record.detail === 'string') return record.detail;
    if (record.detail && typeof record.detail === 'object') {
      const nested = record.detail as Record<string, unknown>;
      if (typeof nested.detail === 'string') return nested.detail;
    }
  }
  return fallback;
}

export class ArtifactService {
  private static instance: ArtifactService;

  private constructor() {}

  static getInstance(): ArtifactService {
    if (!ArtifactService.instance) {
      ArtifactService.instance = new ArtifactService();
    }
    return ArtifactService.instance;
  }

  async getTemplates(): Promise<ArtifactTemplate[]> {
    const response = await fetch(`${BASE}/artifact-templates`);
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(errorDetail(body, 'Failed to load artifact templates'));
    }
    return response.json();
  }

  async getProfile(profileId: string): Promise<ProfileDetails> {
    const response = await fetch(`${BASE}/profiles/${encodeURIComponent(profileId)}`);
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(errorDetail(body, 'Failed to load profile'));
    }
    return response.json();
  }

  async createArtifact(profileId: string, templateId: string): Promise<{ artifactId: string }> {
    const response = await fetch(`${BASE}/profiles/${encodeURIComponent(profileId)}/artifacts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ template: templateId }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(errorDetail(body, 'Failed to create artifact'));
    }
    return response.json();
  }

  async generateMarkdown(profileId: string, artifactId: string): Promise<string> {
    const response = await fetch(`${BASE}/generate/artifact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile_id: profileId,
        artifact_id: artifactId,
        output_format: 'markdown',
      }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(errorDetail(body, 'Failed to generate preview'));
    }
    return response.text();
  }

  async generateDocx(profileId: string, artifactId: string): Promise<Blob> {
    const response = await fetch(`${BASE}/generate/artifact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile_id: profileId,
        artifact_id: artifactId,
        output_format: 'docx',
      }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(errorDetail(body, 'Failed to generate DOCX'));
    }
    return response.blob();
  }

  downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}
