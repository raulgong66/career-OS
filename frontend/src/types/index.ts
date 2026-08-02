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

export type InterviewSessionState = 'draft' | 'ready' | 'in_progress' | 'paused' | 'completed' | 'reviewed' | 'archived';

export interface EvidenceCitation {
  elementType: string;
  elementId: string;
  quote: string | null;
}

export interface SuggestedAnswerOutline {
  situation: string | null;
  task: string | null;
  action: string | null;
  result: string | null;
  evidence: EvidenceCitation[];
  achievement: string | null;
}

export interface InterviewQuestionInstance {
  id: string;
  session_id: string;
  question_text: string;
  category: string;
  difficulty: string;
  competency_ids: string[];
  context_refs: Array<{ id: string; type: string }>;
  evidence_citations: EvidenceCitation[];
  order: number;
  time_limit_seconds: number | null;
  suggested_answer?: SuggestedAnswerOutline;
}

export interface AnswerEvaluation {
  covers_claim: boolean;
  has_metric: boolean;
  cites_evidence: boolean;
  follows_structure: boolean;
  matches_question_competencies: boolean;
  citations: EvidenceCitation[];
}

export interface InterviewFeedback {
  id: string;
  question_id: string;
  answer_id: string;
  missing: string[];
  improvement_recommendation: string | null;
  citations: EvidenceCitation[];
}

export interface InterviewAnswer {
  id: string;
  session_id: string;
  question_id: string;
  text: string;
  answered_at: string | null;
  duration_seconds: number | null;
  evaluation?: AnswerEvaluation;
  feedback?: InterviewFeedback;
}

export interface SessionMetrics {
  total_questions: number;
  answered_questions: number;
  average_duration_seconds: number | null;
  total_duration_seconds: number | null;
}

export interface InterviewSummary {
  total_questions: number;
  answered_questions: number;
  covered_claims: number;
  metric_citations: number;
  evidence_citations: number;
  structured_answers: number;
  strong_answers: number;
  weak_answers: number;
}

export interface EvaluationSummary {
  total_answers: number;
  coverage: number;
  evidence: number;
  claim_alignment: number;
  measurability: number;
  structure: number;
  inconsistent_answers: number;
}

export interface InterviewSession {
  id: string;
  plan_ref: string;
  profile_id: string;
  state: InterviewSessionState;
  questions: InterviewQuestionInstance[];
  answers: InterviewAnswer[];
  started_at: string | null;
  completed_at: string | null;
  paused_at: string | null;
  metrics?: SessionMetrics;
  summary?: InterviewSummary;
  metadata?: Record<string, unknown>;
}

export interface InterviewReport {
  id: string;
  session_id: string;
  profile_id: string;
  plan_ref: string;
  summary: InterviewSummary;
  session_metrics: SessionMetrics;
  answers: InterviewAnswer[];
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
}

export interface SubmitAnswerResponse {
  session: InterviewSession;
  answer: InterviewAnswer;
}

export interface NextStepResponse {
  completed: boolean;
  session: InterviewSession;
  question?: InterviewQuestionInstance;
  report?: InterviewReport;
}
