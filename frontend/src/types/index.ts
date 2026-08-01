export interface ProfileSummary {
  id: string;
  name: string;
  headline: string;
  artifactCount: number;
  artifactIds: string[];
  importedAt: string;
}

export interface DateRange {
  start?: string;
  end?: string;
  isCurrent?: boolean;
  label?: string;
}

export interface ProfessionalSummary {
  id: string;
  label: string;
  text: string;
}

export interface Experience {
  id: string;
  title: string;
  organization: string;
  dateRange: DateRange | null;
  scope: string;
  engagementType: string;
}

export interface Skill {
  id: string;
  name: string;
  category: string;
  description: string;
  proficiency?: string;
}

export interface Education {
  id: string;
  institution: string;
  program: string;
  fieldOfStudy: string;
  dateRange: DateRange | null;
}

export interface Certification {
  id: string;
  name: string;
  issuer: string;
  dateRange: DateRange | null;
}

export interface Project {
  id: string;
  name: string;
  description: string;
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
    status: 'current' | 'stale';
  }>;
  summary: string | null;
  importedAt: string;
  professionalSummaries: ProfessionalSummary[];
  experiences: Experience[];
  skills: Skill[];
  education: Education[];
  certifications: Certification[];
  projects: Project[];
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

export type QualitativeLevel = 'high' | 'medium' | 'low';

export type RecommendationConfidence = QualitativeLevel;
export type RecommendationPriority = QualitativeLevel;
export type RecommendationImpact = QualitativeLevel;

export interface ProfileRecommendation {
  id: string;
  title: string;
  reason: string;
  explanation: string;
  suggested_action: string;
  examples: string[];
  priority: RecommendationPriority;
  estimated_impact: RecommendationImpact;
  detected_pattern: string;
  missing_information: string[];
  recruiter_impact: string;
  triggered_rule: string;
  element_id: string | null;
  element_type: 'profile' | 'experience' | 'skill' | 'achievement' | 'project' | 'certification' | null;
  confidence: RecommendationConfidence;
  future_evidence: Record<string, unknown>;
}

export interface AnalyzeResponse {
  engine_version: string;
  generated_at: string;
  profile_id: string;
  findings: Array<Record<string, unknown>>;
  findings_by_type: Record<string, Array<Record<string, unknown>>>;
  recommendations: ProfileRecommendation[];
  summary: Record<string, unknown>;
  execution_stats: Record<string, unknown>;
}

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
