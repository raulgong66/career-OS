import type { Recommendation, OptimizationStatus } from '../types';

interface GenerateArtifactResponse {
  artifact: string;
  optimizationStatus: OptimizationStatus | null;
  optimizationMessage: string;
  recommendations: Recommendation[];
}

export class TailoringService {
  private static instance: TailoringService;
  private readonly API_BASE_URL = 'http://localhost:8000';

  private constructor() {}

  static getInstance(): TailoringService {
    if (!TailoringService.instance) {
      TailoringService.instance = new TailoringService();
    }
    return TailoringService.instance;
  }

  async generateTailoredArtifact(
    profilePath: string,
    artifactId: string,
    outputFormat: string,
    jobDescription: string
  ): Promise<GenerateArtifactResponse> {
    try {
      const response = await fetch(`${this.API_BASE_URL}/generate/artifact`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          profile_path: profilePath,
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
      const recommendationsHeader = response.headers.get('X-Recommendations');
      
      let recommendations: Recommendation[] = [];
      if (recommendationsHeader) {
        try {
          recommendations = JSON.parse(recommendationsHeader);
        } catch (e) {
          console.error('Failed to parse recommendations header:', e);
        }
      }

      return {
        artifact,
        optimizationStatus: (optimizationStatusHeader as OptimizationStatus) || null,
        optimizationMessage: optimizationMessageHeader || '',
        recommendations,
      };
    } catch (error) {
      console.error('Failed to generate tailored artifact:', error);
      throw error;
    }
  }
}
