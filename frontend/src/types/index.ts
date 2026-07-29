export interface ProfileSummary {
  id: string;
  name: string;
  headline: string;
  artifactCount: number;
  artifactIds: string[];
  importedAt: string;
}

export interface ProfileDetails {
  id: string;
  person: {
    firstName: string;
    lastName: string;
    headline: string;
    city: string | null;
    country: string | null;
    languages: Array<{ name: string; proficiency: string }>;
  };
  artifacts: Array<{
    id: string;
    type: string;
    name: string;
    sourceCount: number;
  }>;
  summary: string | null;
  importedAt: string;
}

export interface ImportResponse {
  profileId: string;
  profile: ProfileSummary;
}

export interface ProfileInfo {
  id: string;
  name: string;
  artifactCount: number;
  artifactIds: string[];
  headline: string;
  importedAt: string;
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
