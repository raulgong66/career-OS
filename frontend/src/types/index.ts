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

export interface ArtifactTemplate {
  id: string;
  displayName: string;
  artifactType: string;
}

export interface TemplatePreview {
  markdown: string;
  source_count: number;
  estimated_health_score: number | null;
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

export interface HealthDimensionScore {
  name: string;
  score: number;
  weight: number;
}

export interface QualityCitation {
  entity_id: string;
  entity_type: string;
  property_path: string;
  snippet: string;
}

export type ResolutionType = 'auto' | 'guided' | 'none';

export interface QualityFinding {
  rule_id: string;
  dimension: string;
  element_id: string;
  element_type: string;
  title: string;
  reason: string;
  suggested_action: string;
  resolution_type: ResolutionType;
  evidence_refs: string[];
  priority: RecommendationPriority;
  estimated_impact: RecommendationImpact;
  confidence: RecommendationConfidence;
  citations: QualityCitation[];
}

export interface QualityReport {
  health_score: number;
  dimensions: HealthDimensionScore[];
  findings: QualityFinding[];
  citations: QualityCitation[];
}

export type UnifiedRecommendationSource = 'profile_quality' | 'optimization';

export interface UnifiedRecommendation {
  id: string;
  source: UnifiedRecommendationSource;
  rule_id: string;
  element_id: string;
  element_type: string;
  title: string;
  reason: string;
  suggested_action: string;
  resolution_type: ResolutionType;
  evidence_refs: string[];
  priority: RecommendationPriority;
  estimated_impact: RecommendationImpact;
  confidence: RecommendationConfidence;
  jd_match_score: number | null;
  context_match_score: number | null;
  weighted_total: number | null;
}

export interface QueueFilters {
  priority: '' | RecommendationPriority;
  resolutionType: '' | ResolutionType;
}

export interface ResolutionPayload {
  triggeredRule: string;
  elementId: string;
  skillIds: string[];
  experienceIds: string[];
  technologies: string[];
  achievementStatement: string;
}

export type InterviewSessionState =
  | 'draft'
  | 'ready'
  | 'in_progress'
  | 'paused'
  | 'completed'
  | 'reviewed'
  | 'archived';

export interface EvidenceReference {
  id: string;
  type: string;
}

export interface InterviewQuestion {
  id: string;
  category: string;
  text: string;
  competency_ids: string[];
  context_refs: EvidenceReference[];
  evidence_citations: EvidenceReference[];
  difficulty: string;
}

export interface InterviewQuestionInstance {
  index: number;
  total: number;
  question: InterviewQuestion;
}

export interface InterviewAnswerRecord {
  question_id: string;
  text: string;
  evidence_references: EvidenceReference[];
}

export interface InterviewSession {
  session_id: string;
  profile_id: string;
  state: InterviewSessionState;
  current_question_index: number;
  question_count: number;
  answered_count: number;
  current_question: InterviewQuestionInstance | null;
  answers: InterviewAnswerRecord[];
  metadata: Record<string, unknown>;
}

export type FeedbackSeverity = 'info' | 'warning' | 'error';

export interface InterviewFeedback {
  code: string;
  message: string;
  severity: FeedbackSeverity;
}

export interface AnswerEvaluation {
  question_id: string;
  coverage_score: number;
  evidence_score: number;
  structure_score: number;
  overall_score: number;
  feedback: InterviewFeedback[];
}

export interface SubmitAnswerResponse {
  session: InterviewSession;
  evaluation: AnswerEvaluation;
}

export interface InterviewSummary {
  session_id: string;
  question_count: number;
  answered_questions: number;
  average_score: number;
  feedback: InterviewFeedback[];
}

export interface InterviewReport {
  session_id: string;
  summary: InterviewSummary;
}

export interface AdvanceSessionResponse {
  completed: boolean;
  session: InterviewSession;
  next_question: InterviewQuestionInstance | null;
  report: InterviewReport | null;
}
