export interface Profile {
  id: string;
  person: {
    firstName: string;
    lastName: string;
  };
  artifacts: Artifact[];
}

export interface Artifact {
  id: string;
  type: string;
  name: string;
  sourceRefs: SourceRef[];
}

export interface SourceRef {
  id: string;
  type: string;
}

export interface Recommendation {
  id: string;
  type: string;
  operation: 'ADD' | 'UPDATE' | 'MOVE' | 'REMOVE';
  displayName: string;
  details: Record<string, unknown>;
  evidence: Array<Record<string, unknown>>;
  scores: Record<string, number>;
}

export interface AnalysisResult {
  matchScore: number;
  strengths: string[];
  missingSkills: string[];
  recommendations: Recommendation[];
  timeline: TimelineStep[];
}

export interface TimelineStep {
  id: string;
  label: string;
  status: 'pending' | 'processing' | 'completed';
}

export interface TailorRequest {
  profile: Profile;
  artifactId: string;
  jobDescription: string;
}
