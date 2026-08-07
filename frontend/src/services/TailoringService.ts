import type { ProfileDetails, Recommendation, OptimizationStatus, OptimizationSummary, ProfileInfo } from '../types';

interface GenerateArtifactResponse {
  artifact: string;
  optimizationStatus: OptimizationStatus | null;
  optimizationMessage: string;
  optimizationSummary: OptimizationSummary | null;
  recommendations: Recommendation[];
}

interface RegenerateArtifactResponse {
  artifactId: string;
  artifact: string;
  status: 'current' | 'stale';
  outputFormat: string;
  profile?: ProfileDetails;
  optimizationStatus?: OptimizationStatus | null;
  optimizationMessage?: string;
  optimizationSummary?: OptimizationSummary | null;
  recommendations?: Recommendation[];
}

export class TailoringService {
  private static instance: TailoringService;
  private readonly BASE = '';

  private constructor() {}

  static getInstance(): TailoringService {
    if (!TailoringService.instance) {
      TailoringService.instance = new TailoringService();
    }
    return TailoringService.instance;
  }

  async getProfiles(): Promise<ProfileInfo[]> {
    const response = await fetch(`${this.BASE}/profiles`);
    if (!response.ok) {
      throw new Error(`Failed to load profiles: ${response.status}`);
    }
    return response.json();
  }

  async generateTailoredArtifact(
    profileId: string,
    artifactId: string,
    outputFormat: string,
    jobDescription: string
  ): Promise<GenerateArtifactResponse> {
    try {
      const response = await fetch(`${this.BASE}/generate/artifact`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          profile_id: profileId,
          artifact_id: artifactId,
          output_format: outputFormat,
          job_description: jobDescription,
        }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const artifact = await response.text();
      
      const optimizationStatusHeader = response.headers.get('X-Optimization-Status');
      const optimizationMessageHeader = response.headers.get('X-Optimization-Message');
      const optimizationSummaryHeader = response.headers.get('X-Optimization-Summary');
      const recommendationsHeader = response.headers.get('X-Recommendations');
      
      let recommendations: Recommendation[] = [];
      if (recommendationsHeader) {
        try {
          recommendations = JSON.parse(recommendationsHeader);
        } catch (e) {
          console.error('Failed to parse recommendations header:', e);
        }
      }

      let summary: OptimizationSummary | null = null;
      if (optimizationSummaryHeader) {
        try {
          summary = JSON.parse(optimizationSummaryHeader);
        } catch (e) {
          console.error('Failed to parse optimization summary header:', e);
        }
      }

      return {
        artifact,
        optimizationStatus: (optimizationStatusHeader as OptimizationStatus) || null,
        optimizationMessage: optimizationMessageHeader || '',
        optimizationSummary: summary,
        recommendations,
      };
    } catch (error) {
      console.error('Failed to generate tailored artifact:', error);
      throw error;
    }
  }

  async regenerateTailoredArtifact(
    profileId: string,
    artifactId: string,
    outputFormat: string,
    jobDescription?: string
  ): Promise<RegenerateArtifactResponse> {
    try {
      const response = await fetch(
        `${this.BASE}/profiles/${profileId}/artifacts/${artifactId}/regenerate`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            output_format: outputFormat,
            ...(jobDescription ? { job_description: jobDescription } : {}),
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      const body: RegenerateArtifactResponse = await response.json();
      if (!body.artifact) {
        throw new Error('Regeneration returned no artifact content.');
      }
      return body;
    } catch (error) {
      console.error('Failed to regenerate tailored artifact:', error);
      throw error;
    }
  }
}
