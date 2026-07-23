import type { AnalysisResult, Recommendation, TailorRequest } from '../types';

export class TailoringService {
  private static instance: TailoringService;

  private constructor() {}

  static getInstance(): TailoringService {
    if (!TailoringService.instance) {
      TailoringService.instance = new TailoringService();
    }
    return TailoringService.instance;
  }

  async analyzeAndTailor(_request: TailorRequest): Promise<AnalysisResult> {
    // Mock implementation - in production this would call the backend API
    return new Promise((resolve) => {
      setTimeout(() => {
        const mockRecommendations: Recommendation[] = [
          {
            id: 'rec-1',
            type: 'skill',
            operation: 'ADD',
            displayName: 'TypeScript',
            details: {},
            evidence: [],
            scores: { relevance: 0.95 },
          },
          {
            id: 'rec-2',
            type: 'skill',
            operation: 'ADD',
            displayName: 'React',
            details: {},
            evidence: [],
            scores: { relevance: 0.90 },
          },
          {
            id: 'rec-3',
            type: 'experience',
            operation: 'ADD',
            displayName: 'Full-stack Development',
            details: {},
            evidence: [],
            scores: { relevance: 0.85 },
          },
        ];

        const mockResult: AnalysisResult = {
          matchScore: 78,
          strengths: [
            'Strong Python background',
            'Experience with cloud infrastructure',
            'Project management skills',
          ],
          missingSkills: [
            'TypeScript',
            'React',
            'GraphQL',
          ],
          recommendations: mockRecommendations,
          timeline: [
            { id: '1', label: 'Load Profile', status: 'completed' },
            { id: '2', label: 'Analyze Role', status: 'completed' },
            { id: '3', label: 'Match Experience', status: 'completed' },
            { id: '4', label: 'Apply Recommendations', status: 'completed' },
            { id: '5', label: 'Generate CV', status: 'completed' },
          ],
        };
        resolve(mockResult);
      }, 2000);
    });
  }

  async getRecommendations(_artifactId: string, _jobDescription: string): Promise<Recommendation[]> {
    // Mock implementation
    return new Promise((resolve) => {
      setTimeout(() => {
        const mockRecommendations: Recommendation[] = [
          {
            id: 'rec-1',
            type: 'skill',
            operation: 'ADD',
            displayName: 'TypeScript',
            details: {},
            evidence: [],
            scores: { relevance: 0.95 },
          },
          {
            id: 'rec-2',
            type: 'skill',
            operation: 'ADD',
            displayName: 'React',
            details: {},
            evidence: [],
            scores: { relevance: 0.90 },
          },
        ];
        resolve(mockRecommendations);
      }, 1000);
    });
  }
}
