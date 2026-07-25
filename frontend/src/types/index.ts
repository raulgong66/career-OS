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

export type OptimizationStatus = 'already_complete' | 'no_matches' | 'recommendations_available';

export interface OptimizationSummary {
  total_profile_elements: number;
  included_profile_elements: number;
  profile_coverage: number;
  additional_evidence: number;
  skills_evaluated: number;
  experiences_evaluated: number;
  projects_evaluated: number;
  achievements_evaluated: number;
  certifications_evaluated: number;
  education_evaluated: number;
  requirements_detected: number | null;
  requirements_matched: number | null;
  requirement_coverage: number | null;
  matched_requirements: string[];
  target_context_emphasis: string[];
}

export interface OptimizationResult {
  status: OptimizationStatus;
  recommendations: Recommendation[];
  message: string;
  summary: OptimizationSummary | null;
}

export interface ProfileInfo {
  id: string;
  name: string;
  artifactCount: number;
  artifactIds: string[];
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
