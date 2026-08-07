import type { ArtifactTemplate, ProfileDetails, TemplatePreview } from '../types';
import { fetchBlob, fetchJson, fetchText } from './http';

const BASE = '';

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
    return fetchJson<ArtifactTemplate[]>(
      `${BASE}/artifact-templates`,
      undefined,
      'Failed to load artifact templates',
    );
  }

  async getProfile(profileId: string): Promise<ProfileDetails> {
    return fetchJson<ProfileDetails>(
      `${BASE}/profiles/${encodeURIComponent(profileId)}`,
      undefined,
      'Failed to load profile',
    );
  }

  async createArtifact(profileId: string, templateId: string): Promise<{ artifactId: string }> {
    return fetchJson<{ artifactId: string }>(
      `${BASE}/profiles/${encodeURIComponent(profileId)}/artifacts`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template: templateId }),
      },
      'Failed to create artifact',
    );
  }

  async previewTemplate(templateId: string, profileId: string): Promise<TemplatePreview> {
    return fetchJson<TemplatePreview>(
      `${BASE}/artifact-templates/${encodeURIComponent(templateId)}/preview`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id: profileId }),
      },
      'Failed to render template preview',
    );
  }

  async generateMarkdown(profileId: string, artifactId: string): Promise<string> {
    return fetchText(
      `${BASE}/generate/artifact`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile_id: profileId,
          artifact_id: artifactId,
          output_format: 'markdown',
        }),
      },
      'Failed to generate preview',
    );
  }

  async generateDocx(profileId: string, artifactId: string): Promise<Blob> {
    return fetchBlob(
      `${BASE}/generate/artifact`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile_id: profileId,
          artifact_id: artifactId,
          output_format: 'docx',
        }),
      },
      'Failed to generate DOCX',
    );
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
