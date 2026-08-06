import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { TailoringService } from '../services/TailoringService';
import { DocumentService } from '../services/DocumentService';
import { ProfileService } from '../services/ProfileService';
import type {
  Recommendation,
  OptimizationStatus,
  OptimizationSummary,
  ProfileInfo,
  ProfileDetails,
  ProfileRecommendation,
  RecommendationImpact,
  RecommendationPriority,
} from '../types';

type RequestStatus = 'idle' | 'analyzing' | 'generating' | 'success' | 'error';

interface ArtifactLabels {
  resultHeading: string;
  emptyState: string;
  completeMessage: string;
}

const PRIORITY_STYLES: Record<RecommendationPriority, string> = {
  high: 'bg-red-100 text-red-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-gray-100 text-gray-700',
};

const IMPACT_STYLES: Record<RecommendationImpact, string> = {
  high: 'bg-green-100 text-green-800',
  medium: 'bg-blue-100 text-blue-800',
  low: 'bg-gray-100 text-gray-700',
};

function capitalizeLevel(level: string): string {
  return level ? level.charAt(0).toUpperCase() + level.slice(1) : level;
}

const ARTIFACT_LABELS: Record<string, ArtifactLabels> = {
  CV: {
    resultHeading: 'Tailored CV',
    emptyState: 'Your tailored CV will appear here',
    completeMessage: 'CV is already complete',
  },
  INTEREST_LETTER: {
    resultHeading: 'Interest Letter',
    emptyState: 'Your interest letter will appear here',
    completeMessage: 'Interest letter is already complete',
  },
};

const TEMPLATE_IDS: Record<string, string> = {
  CV: 'standard_cv',
  INTEREST_LETTER: 'standard_interest_letter',
};

const DEFAULT_LABELS: ArtifactLabels = {
  resultHeading: 'Tailored Document',
  emptyState: 'Your tailored document will appear here',
  completeMessage: 'Document is already complete',
};

function getArtifactLabels(artifactType: string): ArtifactLabels {
  if (artifactType in ARTIFACT_LABELS) return ARTIFACT_LABELS[artifactType];
  return DEFAULT_LABELS;
}

type ProfileSectionKey =
  | 'professionalSummaries'
  | 'experiences'
  | 'skills'
  | 'certifications'
  | 'projects';

type RecommendationTarget =
  | { kind: 'element'; section: ProfileSectionKey; elementId: string }
  | { kind: 'section'; section: ProfileSectionKey }
  | null;

const SECTION_ELEMENT_KEYS: Record<string, ProfileSectionKey> = {
  experience: 'experiences',
  skill: 'skills',
  certification: 'certifications',
  project: 'projects',
};

const SECTION_ACTION_LABELS: Record<ProfileSectionKey, string> = {
  professionalSummaries: 'Improve Summary',
  experiences: 'Improve Experience',
  skills: 'Improve Skill',
  certifications: 'Improve Certification',
  projects: 'Improve Project',
};

const PRIORITY_RANK: Record<RecommendationPriority, number> = {
  high: 3,
  medium: 2,
  low: 1,
};

const IMPACT_RANK: Record<RecommendationImpact, number> = {
  high: 3,
  medium: 2,
  low: 1,
};

const ELEMENT_TYPE_PLURALS: Record<string, string> = {
  experience: 'experiences',
  skill: 'skills',
  certification: 'certifications',
  project: 'projects',
  achievement: 'achievements',
};

const RESOLVABLE_RULES = new Set([
  'ProjectWithoutSkillsRule',
  'ExperienceNoTechnologiesRule',
  'SkillWithoutExperienceRule',
  'NoMeasurableAchievementRule',
]);

const NUMBER_PATTERN = /\d/;

const BUSINESS_OUTCOME_WORDS = new Set([
  'reduced', 'increased', 'improved', 'decreased', 'saved', 'generated',
  'delivered', 'achieved', 'grew', 'cut', 'boosted', 'optimized',
  'automated', 'accelerated', 'streamlined', 'implemented',
  'revenue', 'cost', 'costs', 'sales', 'profit', 'margin', 'roi',
  'efficiency', 'uptime', 'availability', 'performance', 'latency',
  'turnaround', 'productivity', 'growth', 'conversion', 'retention',
  'throughput', 'capacity', 'scaling', 'downtime', 'outage',
  'usd', 'eur', 'million', 'billion', 'thousand',
]);

function isMeasurableStatement(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) return false;
  if (NUMBER_PATTERN.test(trimmed)) return true;
  const lower = trimmed.toLowerCase();
  return [...BUSINESS_OUTCOME_WORDS].some((word) => {
    const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`\\b${escaped}\\b`).test(lower);
  });
}

type RecommendationGroup = {
  key: string;
  title: string;
  priority: RecommendationPriority;
  impact: RecommendationImpact;
  recommendations: ProfileRecommendation[];
};

function groupRecommendations(recommendations: ProfileRecommendation[]): RecommendationGroup[] {
  const groups = new Map<string, RecommendationGroup>();
  for (const rec of recommendations) {
    const key = `${rec.title}::${rec.triggered_rule ?? ''}`;
    let group = groups.get(key);
    if (!group) {
      group = {
        key,
        title: rec.title,
        priority: rec.priority,
        impact: rec.estimated_impact,
        recommendations: [],
      };
      groups.set(key, group);
    }
    if (PRIORITY_RANK[rec.priority] > PRIORITY_RANK[group.priority]) group.priority = rec.priority;
    if (IMPACT_RANK[rec.estimated_impact] > IMPACT_RANK[group.impact]) group.impact = rec.estimated_impact;
    group.recommendations.push(rec);
  }
  return [...groups.values()];
}

function groupNoun(recommendations: ProfileRecommendation[]): string {
  const types = [...new Set(recommendations.map((rec) => rec.element_type ?? 'profile'))];
  if (types.length === 1) return ELEMENT_TYPE_PLURALS[types[0]] ?? 'profile elements';
  return 'profile elements';
}

function elementFallbackLabel(id: string): string {
  return id.replace(/-/g, ' ');
}

function elementDisplayName(rec: ProfileRecommendation, profile: ProfileDetails | null): string {
  const id = rec.element_id;
  if (!id) return 'Profile';
  if (!profile) return elementFallbackLabel(id);
  switch (rec.element_type) {
    case 'experience':
      return profile.experiences.find((e) => e.id === id)?.title ?? elementFallbackLabel(id);
    case 'skill':
      return profile.skills.find((s) => s.id === id)?.name ?? elementFallbackLabel(id);
    case 'certification':
      return profile.certifications.find((c) => c.id === id)?.name ?? elementFallbackLabel(id);
    case 'project':
      return profile.projects.find((p) => p.id === id)?.name ?? elementFallbackLabel(id);
    case 'achievement':
      return elementFallbackLabel(id);
    default:
      return elementFallbackLabel(id);
  }
}

function renderRecommendationDetails(rec: ProfileRecommendation) {
  return (
    <details className="mt-2.5">
      <summary className="cursor-pointer select-none text-xs font-semibold uppercase tracking-wide text-gray-500 hover:text-gray-700">
        Why CareerOS recommends this
      </summary>
      <div className="mt-2.5 space-y-3">
        {rec.suggested_action && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Suggested Action</p>
            <p className="mt-1 text-sm leading-relaxed text-gray-800">{rec.suggested_action}</p>
          </div>
        )}
        {rec.explanation && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Why it matters</p>
            <p className="mt-1 text-sm leading-relaxed text-gray-700">{rec.explanation}</p>
          </div>
        )}
        {rec.recruiter_impact && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Recruiter Impact</p>
            <p className="mt-1 text-sm leading-relaxed text-gray-700">{rec.recruiter_impact}</p>
          </div>
        )}
        {rec.missing_information && rec.missing_information.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Missing Information</p>
            <ul className="mt-1 space-y-1">
              {rec.missing_information.map((item, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="mt-0.5 inline-block h-3.5 w-3.5 flex-shrink-0 rounded-sm border border-gray-400 bg-white" aria-hidden="true" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {rec.examples && rec.examples.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Examples</p>
            <ul className="mt-1 space-y-1">
              {rec.examples.map((example, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="mt-0.5 text-gray-400" aria-hidden="true">•</span>
                  <span>{example}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {rec.triggered_rule && (
          <p className="text-xs text-gray-400">
            Triggered by: <span className="font-medium text-gray-500">{rec.triggered_rule}</span>
          </p>
        )}
        {rec.confidence && <p className="text-xs text-gray-400">{capitalizeLevel(rec.confidence)} confidence</p>}
      </div>
    </details>
  );
}

function resolveRecommendationTarget(rec: ProfileRecommendation): RecommendationTarget {
  const elementType = rec.element_type;
  if (elementType === 'profile' || !elementType) {
    if (rec.id.startsWith('recommendation_remove_duplicate_skills')) {
      return { kind: 'section', section: 'skills' };
    }
    return { kind: 'section', section: 'professionalSummaries' };
  }
  if (elementType === 'achievement') {
    return { kind: 'section', section: 'experiences' };
  }
  const section = SECTION_ELEMENT_KEYS[elementType];
  if (!section) return null;
  if (!rec.element_id) return { kind: 'section', section };
  return { kind: 'element', section, elementId: rec.element_id };
}

function renderMissingChecklist(
  missing: string[],
  recId: string,
  checked: Set<string>,
  onToggle: (key: string) => void,
  heading = 'CareerOS suggests adding'
) {
  if (!missing.length) return null;
  const keyFor = (item: string) => `${recId}::${item}`;
  return (
    <div className="mt-2 border border-blue-200 bg-blue-50 rounded-md p-3">
      <p className="text-xs font-semibold text-blue-800 uppercase tracking-wide">{heading}</p>
      <ul className="mt-1.5 space-y-1.5">
        {missing.map((item) => {
          const key = keyFor(item);
          return (
            <li key={item} className="flex items-start text-sm text-gray-700">
              <input
                id={key}
                type="checkbox"
                checked={checked.has(key)}
                onChange={() => onToggle(key)}
                className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 rounded-sm border-gray-400 text-blue-600"
              />
              <label htmlFor={key} className="ml-2 cursor-pointer select-none">{item}</label>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function TailoringPage() {
  const navigate = useNavigate();
  const [profiles, setProfiles] = useState<ProfileInfo[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [selectedProfile, setSelectedProfile] = useState<ProfileDetails | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [status, setStatus] = useState<RequestStatus>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [artifact, setArtifact] = useState<string>('');
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [optimizationStatus, setOptimizationStatus] = useState<OptimizationStatus | null>(null);
  const [optimizationMessage, setOptimizationMessage] = useState('');
  const [optimizationSummary, setOptimizationSummary] = useState<OptimizationSummary | null>(null);
  const [currentArtifactId, setCurrentArtifactId] = useState('');
  const [currentArtifactType, setCurrentArtifactType] = useState('');
  const [profileRecommendations, setProfileRecommendations] = useState<ProfileRecommendation[]>([]);
  const [recommendationsLoading, setRecommendationsLoading] = useState(false);
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const labels = getArtifactLabels(currentArtifactType);

  const [reviewedIds, setReviewedIds] = useState<Set<string>>(new Set());
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
  const [checkedChecklistItems, setCheckedChecklistItems] = useState<Set<string>>(new Set());
  const [activeRecId, setActiveRecId] = useState<string | null>(null);

  const [openResolutionId, setOpenResolutionId] = useState<string | null>(null);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [resolutionError, setResolutionError] = useState('');
  const [regenerating, setRegenerating] = useState(false);
  const [regenerateError, setRegenerateError] = useState('');
  const [techKeywords, setTechKeywords] = useState<string[]>([]);
  const [selectedSkillIds, setSelectedSkillIds] = useState<Set<string>>(new Set());
  const [selectedExperienceIds, setSelectedExperienceIds] = useState<Set<string>>(new Set());
  const [selectedTechnologies, setSelectedTechnologies] = useState<Set<string>>(new Set());
  const [techQuery, setTechQuery] = useState('');
  const [achievementStatement, setAchievementStatement] = useState('');
  const [summaryDraft, setSummaryDraft] = useState('');
  const [savingSummary, setSavingSummary] = useState(false);
  const [summarySaveError, setSummarySaveError] = useState('');
  const [summarySaved, setSummarySaved] = useState(false);

  const activeRec =
    activeRecId ? profileRecommendations.find((r) => r.id === activeRecId) ?? null : null;
  const activeTarget = activeRec ? resolveRecommendationTarget(activeRec) : null;
  const activeMissing = activeRec?.missing_information ?? [];

  const isCurrentArtifactStale =
    Boolean(currentArtifactId) &&
    (selectedProfile?.artifacts.find((a) => a.id === currentArtifactId)?.status ?? 'current') === 'stale';

  const totalRecommendations = profileRecommendations.length;
  const reviewedCount = profileRecommendations.filter((r) => reviewedIds.has(r.id)).length;
  const dismissedCount = profileRecommendations.filter((r) => dismissedIds.has(r.id)).length;
  const remainingCount = totalRecommendations - reviewedCount - dismissedCount;
  const reviewProgress =
    totalRecommendations > 0 ? Math.round((reviewedCount / totalRecommendations) * 100) : 0;

  const recommendationGroups = useMemo(() => groupRecommendations(profileRecommendations), [profileRecommendations]);

  const handleGoToSection = (rec: ProfileRecommendation) => {
    const target = resolveRecommendationTarget(rec);
    if (!target) return;
    if (activeRecId === rec.id) {
      setActiveRecId(null);
      return;
    }
    setActiveRecId(rec.id);
    const elementId =
      target.kind === 'element'
        ? `profile-element-${target.section}-${target.elementId}`
        : `profile-section-${target.section}`;
    const el = document.getElementById(elementId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: target.kind === 'section' ? 'start' : 'center' });
    }
  };

  const toggleReviewed = (recId: string) => {
    setReviewedIds((prev) => {
      const next = new Set(prev);
      if (next.has(recId)) {
        next.delete(recId);
      } else {
        next.add(recId);
      }
      return next;
    });
    setDismissedIds((prev) => {
      if (!prev.has(recId)) return prev;
      const next = new Set(prev);
      next.delete(recId);
      return next;
    });
  };

  const toggleChecklistItem = (key: string) => {
    setCheckedChecklistItems((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const canResolve = (rec: ProfileRecommendation): boolean =>
    Boolean(rec.element_id) && RESOLVABLE_RULES.has(rec.triggered_rule);

  const toggleResolutionPanel = (rec: ProfileRecommendation) => {
    if (openResolutionId === rec.id) {
      setOpenResolutionId(null);
      setResolutionError('');
      return;
    }
    setOpenResolutionId(rec.id);
    setResolutionError('');
    setSelectedSkillIds(new Set());
    setSelectedExperienceIds(new Set());
    setSelectedTechnologies(new Set());
    setTechQuery('');
    setAchievementStatement('');
  };

  const toggleSelectedSkill = (skillId: string) => {
    setSelectedSkillIds((prev) => {
      const next = new Set(prev);
      if (next.has(skillId)) {
        next.delete(skillId);
      } else {
        next.add(skillId);
      }
      return next;
    });
  };

  const toggleSelectedExperience = (experienceId: string) => {
    setSelectedExperienceIds((prev) => {
      const next = new Set(prev);
      if (next.has(experienceId)) {
        next.delete(experienceId);
      } else {
        next.add(experienceId);
      }
      return next;
    });
  };

  const toggleSelectedTechnology = (technology: string) => {
    setSelectedTechnologies((prev) => {
      const next = new Set(prev);
      if (next.has(technology)) {
        next.delete(technology);
      } else {
        next.add(technology);
      }
      return next;
    });
  };

  const filteredTechKeywords = techKeywords.filter((keyword) =>
    keyword.toLowerCase().includes(techQuery.trim().toLowerCase())
  );

  const applyResolution = async (rec: ProfileRecommendation) => {
    if (!selectedProfile) return;
    setResolvingId(rec.id);
    setResolutionError('');
    try {
      const updated = await ProfileService.getInstance().resolveRecommendation(selectedProfileId, {
        triggeredRule: rec.triggered_rule,
        elementId: rec.element_id ?? '',
        skillIds: [...selectedSkillIds],
        experienceIds: [...selectedExperienceIds],
        technologies: [...selectedTechnologies],
        achievementStatement,
      });
      setSelectedProfile(updated);
      const analysis = await ProfileService.getInstance().analyzeProfile(selectedProfileId);
      setProfileRecommendations(analysis.recommendations ?? []);
      setReviewedIds(new Set());
      setDismissedIds(new Set());
      if ((analysis.recommendations ?? []).some((r) => r.id === rec.id)) {
        setOpenResolutionId(rec.id);
        setResolutionError(
          rec.triggered_rule === 'NoMeasurableAchievementRule'
            ? 'This recommendation could not be cleared automatically. Make sure your achievement states a quantified outcome (a number, percentage, or business result), then try again.'
            : 'This recommendation could not be cleared automatically. Check that your selections name a recognized technology, then try again.'
        );
      } else {
        setOpenResolutionId(null);
        setActiveRecId(null);
      }
    } catch (err) {
      setResolutionError(err instanceof Error ? err.message : 'Failed to apply changes');
    } finally {
      setResolvingId(null);
    }
  };

  const handleRegenerate = async () => {
    if (!selectedProfile || !currentArtifactId) return;
    setRegenerating(true);
    setRegenerateError('');
    try {
      const service = TailoringService.getInstance();
      const response = await service.regenerateTailoredArtifact(
        selectedProfileId,
        currentArtifactId,
        'markdown'
      );
      setArtifact(response.artifact);
      if (response.profile) {
        setSelectedProfile(response.profile);
      }
    } catch (err) {
      setRegenerateError(
        err instanceof Error ? err.message : 'Failed to regenerate document'
      );
    } finally {
      setRegenerating(false);
    }
  };

  const saveSummary = async () => {
    if (!selectedProfile) return;
    setSavingSummary(true);
    setSummarySaveError('');
    try {
      const updated = await ProfileService.getInstance().resolveRecommendation(selectedProfileId, {
        triggeredRule: 'GenericSummaryRule',
        elementId: '',
        skillIds: [],
        experienceIds: [],
        technologies: [],
        achievementStatement: '',
        summaryText: summaryDraft,
      });
      setSelectedProfile(updated);
      setSummaryDraft(updated.professionalSummaries?.[0]?.text ?? '');
      setSummarySaved(true);
      const analysis = await ProfileService.getInstance().analyzeProfile(selectedProfileId);
      setProfileRecommendations(analysis.recommendations ?? []);
      setReviewedIds(new Set());
      setDismissedIds(new Set());
      if (activeRecId && !(analysis.recommendations ?? []).some((r) => r.id === activeRecId)) {
        setActiveRecId(null);
      }
    } catch (err) {
      setSummarySaveError(err instanceof Error ? err.message : 'Failed to save summary');
    } finally {
      setSavingSummary(false);
    }
  };

  const renderResolutionPanel = (rec: ProfileRecommendation) => {
    if (!selectedProfile || !canResolve(rec)) return null;
    const nothingSelected =
      rec.triggered_rule === 'ExperienceNoTechnologiesRule'
        ? selectedTechnologies.size === 0
        : rec.triggered_rule === 'SkillWithoutExperienceRule'
          ? selectedExperienceIds.size === 0
          : rec.triggered_rule === 'NoMeasurableAchievementRule'
            ? !isMeasurableStatement(achievementStatement)
            : selectedSkillIds.size === 0 && selectedExperienceIds.size === 0;
    return (
      <div className="mt-3 border border-emerald-200 bg-emerald-50 rounded-md p-3">
        <p className="text-xs font-semibold text-emerald-800 uppercase tracking-wide">Resolve inline</p>
        {rec.triggered_rule === 'ProjectWithoutSkillsRule' && (
          <>
            <p className="mt-1 text-sm text-gray-700">
              Tag this project with the skills it demonstrates. You can also link related experiences.
            </p>
            <p className="mt-2 text-xs font-semibold text-gray-600 uppercase tracking-wide">Skills</p>
            <ul className="mt-1 max-h-40 space-y-1 overflow-y-auto">
              {selectedProfile.skills.map((skill) => (
                <li key={skill.id} className="flex items-start text-sm text-gray-700">
                  <input
                    id={`${rec.id}-skill-${skill.id}`}
                    type="checkbox"
                    checked={selectedSkillIds.has(skill.id)}
                    onChange={() => toggleSelectedSkill(skill.id)}
                    className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 rounded-sm border-gray-400 text-emerald-600"
                  />
                  <label htmlFor={`${rec.id}-skill-${skill.id}`} className="ml-2 cursor-pointer select-none">{skill.name}</label>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs font-semibold text-gray-600 uppercase tracking-wide">Related experiences</p>
            <ul className="mt-1 max-h-40 space-y-1 overflow-y-auto">
              {selectedProfile.experiences.map((exp) => (
                <li key={exp.id} className="flex items-start text-sm text-gray-700">
                  <input
                    id={`${rec.id}-experience-${exp.id}`}
                    type="checkbox"
                    checked={selectedExperienceIds.has(exp.id)}
                    onChange={() => toggleSelectedExperience(exp.id)}
                    className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 rounded-sm border-gray-400 text-emerald-600"
                  />
                  <label htmlFor={`${rec.id}-experience-${exp.id}`} className="ml-2 cursor-pointer select-none">
                    {exp.title}
                    {exp.organization ? ` — ${exp.organization}` : ''}
                  </label>
                </li>
              ))}
            </ul>
          </>
        )}
        {rec.triggered_rule === 'ExperienceNoTechnologiesRule' && (
          <>
            <p className="mt-1 text-sm text-gray-700">
              Select the technologies you used in this role. They will be appended to the experience description.
            </p>
            <input
              type="search"
              value={techQuery}
              onChange={(event) => setTechQuery(event.target.value)}
              placeholder="Filter technologies..."
              className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-800 placeholder-gray-400 focus:border-emerald-500 focus:outline-none"
            />
            <ul className="mt-2 max-h-44 space-y-1 overflow-y-auto rounded-md border border-emerald-100 bg-white p-2">
              {filteredTechKeywords.length > 0 ? (
                filteredTechKeywords.map((keyword) => (
                  <li key={keyword} className="flex items-start text-sm text-gray-700">
                    <input
                      id={`${rec.id}-tech-${keyword}`}
                      type="checkbox"
                      checked={selectedTechnologies.has(keyword)}
                      onChange={() => toggleSelectedTechnology(keyword)}
                      className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 rounded-sm border-gray-400 text-emerald-600"
                    />
                    <label htmlFor={`${rec.id}-tech-${keyword}`} className="ml-2 cursor-pointer select-none">{keyword}</label>
                  </li>
                ))
              ) : (
                <li className="text-sm text-gray-400">No technologies match your filter.</li>
              )}
            </ul>
          </>
        )}
        {rec.triggered_rule === 'SkillWithoutExperienceRule' && (
          <>
            <p className="mt-1 text-sm text-gray-700">
              Choose the experience entries that demonstrate this skill.
            </p>
            <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto">
              {selectedProfile.experiences.map((exp) => (
                <li key={exp.id} className="flex items-start text-sm text-gray-700">
                  <input
                    id={`${rec.id}-experience-${exp.id}`}
                    type="checkbox"
                    checked={selectedExperienceIds.has(exp.id)}
                    onChange={() => toggleSelectedExperience(exp.id)}
                    className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 rounded-sm border-gray-400 text-emerald-600"
                  />
                  <label htmlFor={`${rec.id}-experience-${exp.id}`} className="ml-2 cursor-pointer select-none">
                    {exp.title}
                    {exp.organization ? ` — ${exp.organization}` : ''}
                  </label>
                </li>
              ))}
            </ul>
          </>
        )}
        {rec.triggered_rule === 'NoMeasurableAchievementRule' && (
          <>
            <p className="mt-1 text-sm text-gray-700">
              Write a measurable achievement for this role. Quantify the outcome so
              reviewers can see the value you delivered.
            </p>
            <textarea
              value={achievementStatement}
              onChange={(event) => setAchievementStatement(event.target.value)}
              rows={3}
              placeholder="e.g. Reduced deployment time by 60%"
              className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-800 placeholder-gray-400 focus:border-emerald-500 focus:outline-none"
            />
            {achievementStatement.trim() && !isMeasurableStatement(achievementStatement) && (
              <p className="mt-1 text-xs text-amber-700">
                Add a number, percentage, or business outcome (e.g. cost, time, growth) so this counts as measurable.
              </p>
            )}
            <div>
              <p className="mt-2 text-xs font-semibold text-gray-600 uppercase tracking-wide">Related skills (optional)</p>
              <ul className="mt-1 max-h-40 space-y-1 overflow-y-auto">
                {selectedProfile.skills.map((skill) => (
                  <li key={skill.id} className="flex items-start text-sm text-gray-700">
                    <input
                      id={`${rec.id}-achievement-skill-${skill.id}`}
                      type="checkbox"
                      checked={selectedSkillIds.has(skill.id)}
                      onChange={() => toggleSelectedSkill(skill.id)}
                      className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 rounded-sm border-gray-400 text-emerald-600"
                    />
                    <label htmlFor={`${rec.id}-achievement-skill-${skill.id}`} className="ml-2 cursor-pointer select-none">{skill.name}</label>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
        {resolutionError && (
          <p className="mt-2 text-sm text-red-600">{resolutionError}</p>
        )}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            onClick={() => applyResolution(rec)}
            disabled={resolvingId === rec.id || nothingSelected}
            className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {resolvingId === rec.id ? 'Applying...' : 'Apply to profile'}
          </button>
          <button
            onClick={() => toggleResolutionPanel(rec)}
            className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <span className="text-xs text-gray-400">Writes canonical profile changes</span>
        </div>
      </div>
    );
  };

  const toggleDismissed = (recId: string) => {
    setDismissedIds((prev) => {
      const next = new Set(prev);
      if (next.has(recId)) {
        next.delete(recId);
      } else {
        next.add(recId);
      }
      return next;
    });
    setReviewedIds((prev) => {
      if (!prev.has(recId)) return prev;
      const next = new Set(prev);
      next.delete(recId);
      return next;
    });
  };

  const loadProfileRecommendations = (profileId: string) => {
    setProfileRecommendations([]);
    setRecommendationsLoading(true);
    setReviewedIds(new Set());
    setDismissedIds(new Set());
    setActiveRecId(null);
    ProfileService.getInstance().analyzeProfile(profileId)
      .then((result) => {
        setProfileRecommendations(result.recommendations ?? []);
      })
      .catch(() => {
        setProfileRecommendations([]);
      })
      .finally(() => {
        setRecommendationsLoading(false);
      });
  };

  useEffect(() => {
    setLoadingProfiles(true);
    const service = TailoringService.getInstance();
    service.getProfiles().then((profiles) => {
      setProfiles(profiles);
      if (profiles.length > 0) {
        setSelectedProfileId(profiles[0].id);
        loadProfileRecommendations(profiles[0].id);
        ProfileService.getInstance().getProfile(profiles[0].id).then((details) => {
          setSelectedProfile(details);
          setSummaryDraft(details.professionalSummaries?.[0]?.text ?? '');
          setSummarySaved(false);
        }).catch(() => {}).finally(() => setLoadingProfiles(false));
      } else {
        setLoadingProfiles(false);
      }
    }).catch(() => {
      setErrorMessage('Unable to load profiles. Please ensure the backend is running.');
      setLoadingProfiles(false);
    });
  }, []);

  useEffect(() => {
    ProfileService.getInstance()
      .getTechnologyKeywords()
      .then((keywords) => setTechKeywords(keywords))
      .catch(() => setTechKeywords([]));
  }, []);

  const handleProfileChange = (profileId: string) => {
    setSelectedProfileId(profileId);
    setSelectedProfile(null);
    loadProfileRecommendations(profileId);
    ProfileService.getInstance().getProfile(profileId).then((details) => {
      setSelectedProfile(details);
      setSummaryDraft(details.professionalSummaries?.[0]?.text ?? '');
      setSummarySaved(false);
      setErrorMessage('');
    }).catch(() => {
      setErrorMessage('Failed to load profile details. Please try again.');
    });
  };

  const generateDocument = async (artifactType: 'CV' | 'INTEREST_LETTER') => {
    if (!jobDescription.trim()) {
      setErrorMessage('Please enter a job description');
      setStatus('error');
      return;
    }

    setErrorMessage('');
    setStatus('analyzing');

    try {
      setArtifact('');
      setRecommendations([]);
      setOptimizationStatus(null);
      setOptimizationMessage('');
      setOptimizationSummary(null);

      let artifactId: string | null = null;
      const existing = selectedProfile?.artifacts.find((a: { type: string }) => a.type === artifactType);
      if (existing) {
        artifactId = existing.id;
      } else {
        const result = await ProfileService.getInstance().createArtifact(selectedProfileId, TEMPLATE_IDS[artifactType]);
        const details = await ProfileService.getInstance().getProfile(selectedProfileId);
        setSelectedProfile(details);
        artifactId = result.artifactId;
      }

      setCurrentArtifactId(artifactId);
      setCurrentArtifactType(artifactType);

      const generatingTimeout = setTimeout(() => {
        setStatus('generating');
      }, 800);

      const service = TailoringService.getInstance();
      const response = await service.generateTailoredArtifact(
        selectedProfileId,
        artifactId,
        'markdown',
        jobDescription
      );

      clearTimeout(generatingTimeout);

      setArtifact(response.artifact);
      setRecommendations(response.recommendations);
      setOptimizationStatus(response.optimizationStatus);
      setOptimizationMessage(response.optimizationMessage);
      setOptimizationSummary(response.optimizationSummary);
      setStatus('success');
    } catch (error) {
      setStatus('error');
      setErrorMessage(
        error instanceof Error && error.message.includes('Failed to fetch')
          ? 'Unable to connect to the server. Please ensure the backend is running.'
          : error instanceof Error
          ? error.message
          : 'Failed to generate document'
      );
    }
  };

  const formatDateRange = (dr: import('../types').DateRange | null): string => {
    if (!dr) return '';
    if (dr.label) return dr.label;
    const parts: string[] = [];
    if (dr.start) parts.push(dr.start);
    if (dr.isCurrent) {
      parts.push('Present');
    } else if (dr.end) {
      parts.push(dr.end);
    }
    return parts.join(' – ');
  };

  const renderEntitySections = (
    profile: import('../types').ProfileDetails,
    activeTarget: RecommendationTarget,
    activeMissing: string[],
  ) => {
    const isSectionActive = (section: ProfileSectionKey) =>
      activeTarget?.kind === 'section' && activeTarget.section === section;

    const isElementActive = (section: ProfileSectionKey, elementId: string) =>
      activeTarget?.kind === 'element' &&
      activeTarget.section === section &&
      activeTarget.elementId === elementId;

    const sectionHeaderClass = (section: ProfileSectionKey) =>
      `px-3 py-2 bg-gray-50 ${isSectionActive(section) ? 'border-l-4 border-blue-500 bg-blue-50' : ''}`;

    const elementRowClass = (active: boolean) =>
      `px-3 py-2 ${active ? 'bg-blue-50 border-l-4 border-blue-500' : ''}`;

    return (
      <div className="space-y-4">
        {/* Professional Summary */}
        <div id="profile-section-professionalSummaries" className="border border-gray-200 rounded-md divide-y divide-gray-200">
          <div className={sectionHeaderClass('professionalSummaries')}>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Professional Summary</h3>
          </div>
          {isSectionActive('professionalSummaries') && renderMissingChecklist(activeMissing, activeRec?.id ?? '', checkedChecklistItems, toggleChecklistItem)}
          {isSectionActive('professionalSummaries') ? (
            <div className="px-3 py-3">
              <p className="text-xs font-medium text-gray-500 mb-1">
                {profile.professionalSummaries[0]?.label || 'Professional Summary'}
              </p>
              <textarea
                value={summaryDraft}
                onChange={(event) => {
                  setSummaryDraft(event.target.value);
                  setSummarySaved(false);
                }}
                rows={4}
                placeholder="Write 2-3 lines covering your role, your strongest skills, and one quantified highlight."
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none"
              />
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <button
                  onClick={saveSummary}
                  disabled={savingSummary || !summaryDraft.trim()}
                  className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {savingSummary ? 'Saving...' : 'Save summary'}
                </button>
                {summarySaved && (
                  <span className="text-xs text-green-600">Summary saved to your profile.</span>
                )}
                {summarySaveError && (
                  <span className="text-xs text-red-600">{summarySaveError}</span>
                )}
              </div>
            </div>
          ) : profile.professionalSummaries.length === 0 ? (
            <div className="px-3 py-4">
              <p className="text-sm text-gray-400 italic">No professional summary yet.</p>
            </div>
          ) : (
            profile.professionalSummaries.map((ps) => (
              <div key={ps.id} className="px-3 py-2">
                {ps.label && <p className="text-xs font-medium text-gray-500 mb-1">{ps.label}</p>}
                <p className="text-sm text-gray-700 leading-relaxed">{ps.text}</p>
              </div>
            ))
          )}
        </div>

        {/* Experience */}
        <div id="profile-section-experiences" className="border border-gray-200 rounded-md divide-y divide-gray-200">
          <div className={sectionHeaderClass('experiences')}>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Experience</h3>
          </div>
          {isSectionActive('experiences') && renderMissingChecklist(activeMissing, activeRec?.id ?? '', checkedChecklistItems, toggleChecklistItem)}
          {profile.experiences.length === 0 ? (
            <div className="px-3 py-4">
              <p className="text-sm text-gray-400 italic">No experience entries available.</p>
            </div>
          ) : (
            profile.experiences.map((exp) => {
              const elementActive = isElementActive('experiences', exp.id);
              return (
                <div
                  key={exp.id}
                  id={`profile-element-experiences-${exp.id}`}
                  className={elementRowClass(elementActive)}
                >
                  <p className="text-sm font-medium text-gray-900">{exp.title}</p>
                  {(exp.organization || exp.engagementType) && (
                    <p className="text-xs text-gray-500 mt-0.5">
                      {[exp.organization, exp.engagementType].filter(Boolean).join(' · ')}
                    </p>
                  )}
                  {formatDateRange(exp.dateRange) && (
                    <p className="text-xs text-gray-400 mt-0.5">{formatDateRange(exp.dateRange)}</p>
                  )}
                  {exp.scope && (
                    <p className="text-sm text-gray-700 mt-1 leading-relaxed">{exp.scope}</p>
                  )}
                  {elementActive && renderMissingChecklist(activeMissing, activeRec?.id ?? '', checkedChecklistItems, toggleChecklistItem)}
                </div>
              );
            })
          )}
        </div>

        {/* Skills */}
        <div id="profile-section-skills" className="border border-gray-200 rounded-md divide-y divide-gray-200">
          <div className={sectionHeaderClass('skills')}>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Skills</h3>
          </div>
          {isSectionActive('skills') && renderMissingChecklist(activeMissing, activeRec?.id ?? '', checkedChecklistItems, toggleChecklistItem)}
          {profile.skills.length === 0 ? (
            <div className="px-3 py-4">
              <p className="text-sm text-gray-400 italic">No skills available.</p>
            </div>
          ) : (
            <div className="px-3 py-2">
              <div className="flex flex-wrap gap-1.5">
                {profile.skills.map((skill) => {
                  const elementActive = isElementActive('skills', skill.id);
                  return (
                    <span
                      key={skill.id}
                      id={`profile-element-skills-${skill.id}`}
                      className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-medium ${
                        elementActive
                          ? 'bg-blue-200 text-blue-900 border-2 border-blue-500'
                          : 'bg-blue-50 text-blue-700 border border-blue-200'
                      }`}
                      title={skill.description || skill.category || undefined}
                    >
                      {skill.name}
                      {skill.proficiency && (
                        <span className="ml-1 text-blue-400 font-normal">({skill.proficiency})</span>
                      )}
                    </span>
                  );
                })}
              </div>
              {profile.skills.some((s) => isElementActive('skills', s.id)) &&
                renderMissingChecklist(activeMissing, activeRec?.id ?? '', checkedChecklistItems, toggleChecklistItem)}
            </div>
          )}
        </div>

        {/* Education */}
        <div id="profile-section-education" className="border border-gray-200 rounded-md divide-y divide-gray-200">
          <div className="px-3 py-2 bg-gray-50">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Education</h3>
          </div>
          {profile.education.length === 0 ? (
            <div className="px-3 py-4">
              <p className="text-sm text-gray-400 italic">No education entries available.</p>
            </div>
          ) : (
            profile.education.map((edu) => (
              <div key={edu.id} className="px-3 py-2">
                <p className="text-sm font-medium text-gray-900">{edu.program}</p>
                {(edu.institution || edu.fieldOfStudy) && (
                  <p className="text-xs text-gray-500 mt-0.5">
                    {[edu.institution, edu.fieldOfStudy].filter(Boolean).join(' · ')}
                  </p>
                )}
                {formatDateRange(edu.dateRange) && (
                  <p className="text-xs text-gray-400 mt-0.5">{formatDateRange(edu.dateRange)}</p>
                )}
              </div>
            ))
          )}
        </div>

        {/* Certifications */}
        <div id="profile-section-certifications" className="border border-gray-200 rounded-md divide-y divide-gray-200">
          <div className={sectionHeaderClass('certifications')}>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Certifications</h3>
          </div>
          {isSectionActive('certifications') && renderMissingChecklist(activeMissing, activeRec?.id ?? '', checkedChecklistItems, toggleChecklistItem)}
          {profile.certifications.length === 0 ? (
            <div className="px-3 py-4">
              <p className="text-sm text-gray-400 italic">No certifications available.</p>
            </div>
          ) : (
            profile.certifications.map((cert) => {
              const elementActive = isElementActive('certifications', cert.id);
              return (
                <div
                  key={cert.id}
                  id={`profile-element-certifications-${cert.id}`}
                  className={elementRowClass(elementActive)}
                >
                  <p className="text-sm font-medium text-gray-900">{cert.name}</p>
                  {cert.issuer && (
                    <p className="text-xs text-gray-500 mt-0.5">{cert.issuer}</p>
                  )}
                  {formatDateRange(cert.dateRange) && (
                    <p className="text-xs text-gray-400 mt-0.5">{formatDateRange(cert.dateRange)}</p>
                  )}
                  {elementActive && renderMissingChecklist(activeMissing, activeRec?.id ?? '', checkedChecklistItems, toggleChecklistItem)}
                </div>
              );
            })
          )}
        </div>

        {/* Projects */}
        <div id="profile-section-projects" className="border border-gray-200 rounded-md divide-y divide-gray-200">
          <div className={sectionHeaderClass('projects')}>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Projects</h3>
          </div>
          {isSectionActive('projects') && renderMissingChecklist(activeMissing, activeRec?.id ?? '', checkedChecklistItems, toggleChecklistItem)}
          {profile.projects.length === 0 ? (
            <div className="px-3 py-4">
              <p className="text-sm text-gray-400 italic">No projects available.</p>
            </div>
          ) : (
            profile.projects.map((proj) => {
              const elementActive = isElementActive('projects', proj.id);
              return (
                <div
                  key={proj.id}
                  id={`profile-element-projects-${proj.id}`}
                  className={elementRowClass(elementActive)}
                >
                  <p className="text-sm font-medium text-gray-900">{proj.name}</p>
                  {proj.description && (
                    <p className="text-sm text-gray-700 mt-1 leading-relaxed">{proj.description}</p>
                  )}
                  {elementActive && renderMissingChecklist(activeMissing, activeRec?.id ?? '', checkedChecklistItems, toggleChecklistItem)}
                </div>
              );
            })
          )}
        </div>
      </div>
    );
  };

  const renderResume = (content: string) => {
    const lines = content.split('\n');
    return lines.map((line, index) => {
      if (line.startsWith('# ')) {
        return <h3 key={index} className="text-lg font-bold text-gray-900 mt-4 mb-2">{line.slice(2)}</h3>;
      }
      if (line.startsWith('## ')) {
        return <h4 key={index} className="text-base font-semibold text-gray-900 mt-3 mb-1">{line.slice(3)}</h4>;
      }
      if (line.startsWith('- ')) {
        return <li key={index} className="text-sm text-gray-700 ml-4">{line.slice(2)}</li>;
      }
      if (line.trim()) {
        return <p key={index} className="text-sm text-gray-700 mb-1">{line}</p>;
      }
      return <br key={index} />;
    });
  };

  const getRecommendationReason = (rec: Recommendation): string | null => {
    if (rec.evidence && rec.evidence.length > 0) {
      const evidence = rec.evidence[0];
      if (typeof evidence === 'object' && evidence !== null) {
        const reason = (evidence as any).reason || (evidence as any).description;
        if (reason) return reason;
      }
    }
    if (rec.details && typeof rec.details === 'object') {
      const reason = (rec.details as any).reason;
      if (reason) return reason;
    }
    return null;
  };

  const getRecommendationImpact = (rec: Recommendation): string | null => {
    if (rec.details && typeof rec.details === 'object') {
      const impact = (rec.details as any).impact;
      if (impact) return impact;
    }
    return null;
  };

  const getRecommendationConfidence = (rec: Recommendation): number | null => {
    if (rec.scores && Object.keys(rec.scores).length > 0) {
      const scoreValue = Object.values(rec.scores)[0];
      if (typeof scoreValue === 'number') {
        return Math.round(scoreValue * 100);
      }
    }
    return null;
  };

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">CareerOS Platform Alpha</h1>
          <p className="text-sm text-gray-600 mt-1">AI-Powered Document Tailoring</p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="text-sm font-medium text-blue-600 hover:text-blue-800"
        >
          ← Back to Home
        </button>
      </header>

      <div className="flex-1 overflow-hidden">
        <div className="h-full grid grid-cols-1 lg:grid-cols-2">
          {/* Left Panel */}
          <div className="border-r border-gray-200 bg-white p-6 overflow-y-auto">
            {loadingProfiles ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <svg className="animate-spin h-8 w-8 mb-3 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <p className="text-sm">Loading profiles...</p>
              </div>
            ) : (
            <div className="max-w-xl mx-auto space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Source Profile</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Profile</label>
                    <select
                      value={selectedProfileId}
                      onChange={(e) => handleProfileChange(e.target.value)}
                      className="w-full p-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {profiles.length === 0 && <option value="">Loading profiles...</option>}
                      {profiles.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>
                  {selectedProfile && (
                    <>
                      <div className="border border-gray-200 rounded-md divide-y divide-gray-200">
                        <div className="px-3 py-2">
                          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Name</label>
                          <p className="mt-0.5 text-sm text-gray-900">{selectedProfile.person.firstName} {selectedProfile.person.lastName}</p>
                        </div>
                        <div className="px-3 py-2">
                          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Headline</label>
                          <p className="mt-0.5 text-sm text-gray-700">{selectedProfile.person.headline || '—'}</p>
                        </div>
                        <div className="px-3 py-2">
                          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Location</label>
                          <p className="mt-0.5 text-sm text-gray-700">
                            {[selectedProfile.person.city, selectedProfile.person.country].filter(Boolean).join(', ') || '—'}
                          </p>
                        </div>
                        <div className="px-3 py-2">
                          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Languages</label>
                          <p className="mt-0.5 text-sm text-gray-700">
                            {selectedProfile.person.languages.length > 0
                              ? selectedProfile.person.languages.map((l) => `${l.name} (${l.proficiency})`).join(', ')
                              : '—'}
                          </p>
                        </div>
                        {selectedProfile.summary && (
                          <div className="px-3 py-2">
                            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Summary</label>
                            <p className="mt-0.5 text-sm text-gray-700 leading-relaxed">{selectedProfile.summary}</p>
                          </div>
                        )}
                      </div>

                      {/* ── Entity Sections ── */}
                      {renderEntitySections(selectedProfile, activeTarget, activeMissing)}
                    </>
                  )}
                  </div>
                </div>

              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Paste Job Description</h2>
                <textarea
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Paste the job description here..."
                  className="w-full h-48 p-3 border border-gray-300 rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex gap-3">
                {(['CV', 'INTEREST_LETTER'] as const).map((type) => {
                  const isActive = status === 'analyzing' || status === 'generating';
                  const label = type === 'CV' ? 'Generate Tailored CV' : 'Generate Interest Letter';
                  return (
                    <button
                      key={type}
                      onClick={() => generateDocument(type)}
                      disabled={isActive || !jobDescription.trim() || !selectedProfile}
                      className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-md transition-colors duration-200"
                    >
                      {isActive ? (
                        <span className="flex items-center justify-center">
                          <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          {status === 'analyzing' ? 'Analyzing' : 'Generating...'}
                        </span>
                      ) : (
                        label
                      )}
                    </button>
                  );
                })}
              </div>

              {status === 'error' && (
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                  <p className="text-sm text-red-700">{errorMessage}</p>
                </div>
              )}
            </div>
            )}
          </div>

          {/* Right Panel */}
          <div className="bg-gray-50 p-6 overflow-y-auto">
            <div className="max-w-2xl mx-auto space-y-6">

              {/* ── Status Banner ── */}
                    {status === 'success' && optimizationStatus === 'already_complete' && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-5">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-0.5">
                      <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-base font-semibold text-green-800">Optimization Complete</h2>
                      <p className="mt-1 text-sm text-green-700 leading-relaxed">
                        Your profile already contains all verified evidence relevant to this opportunity.
                        No additional profile information needs to be incorporated.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {status === 'success' && optimizationStatus === 'no_matches' && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-5">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-0.5">
                      <svg className="h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-base font-semibold text-blue-800">Analysis Complete</h2>
                      <p className="mt-1 text-sm text-blue-700 leading-relaxed">{optimizationMessage}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Metric Cards ── */}
              {status === 'success' && optimizationSummary && (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Profile Coverage</span>
                      <svg className="h-4 w-4 text-green-400" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
                      </svg>
                    </div>
                    <p className="text-3xl font-bold text-green-600">{optimizationSummary.profile_coverage.toFixed(0)}<span className="text-lg font-semibold">%</span></p>
                    <p className="mt-1.5 text-xs text-gray-500">All profile evidence included</p>
                  </div>

                  <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Job Match</span>
                      <svg className="h-4 w-4 text-blue-400" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
                      </svg>
                    </div>
                    <p className="text-3xl font-bold text-blue-600">{optimizationSummary.requirement_coverage?.toFixed(0) ?? '—'}<span className="text-lg font-semibold">%</span></p>
                    <p className="mt-1.5 text-xs text-gray-500">Requirements satisfied</p>
                  </div>

                  <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Job Requirements</span>
                      <svg className="h-4 w-4 text-purple-400" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                      </svg>
                    </div>
                    <p className="text-3xl font-bold text-purple-600">{optimizationSummary.requirements_detected ?? '—'}</p>
                    <p className="mt-1.5 text-xs text-gray-500">Requirements identified</p>
                  </div>

                  <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Matching Competencies</span>
                      <svg className="h-4 w-4 text-orange-400" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                      </svg>
                    </div>
                    <p className="text-3xl font-bold text-orange-600">{optimizationSummary.matched_requirements.length}</p>
                    <p className="mt-1.5 text-xs text-gray-500">Relevant competencies found</p>
                  </div>
                </div>
              )}

              {/* ── Analysis Explanation ── */}
              {status === 'success' && optimizationSummary && (
                <p className="text-sm text-gray-500 leading-relaxed border-l-2 border-gray-200 pl-4">
                  The AI analyzed the job description, compared it with your professional profile,
                  and generated this tailored document using verified profile evidence.
                </p>
              )}

              {/* ── Job Match Analysis ── */}
              {status === 'success' && optimizationSummary && (optimizationSummary.matched_requirements.length > 0 || optimizationSummary.target_context_emphasis.length > 0) && (
                <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                  <h2 className="text-base font-semibold text-gray-900 mb-4">Job Match Analysis</h2>

                  {optimizationSummary.matched_requirements.length > 0 && (
                    <div className="mb-5">
                      <h3 className="text-sm font-medium text-gray-700 mb-2.5">Matching Competencies</h3>
                      <div className="flex flex-wrap gap-2">
                        {optimizationSummary.matched_requirements.map((req) => (
                          <span key={req} className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                            {req}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {optimizationSummary.target_context_emphasis.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 mb-2.5">Target Context</h3>
                      <div className="flex flex-wrap gap-2">
                        {optimizationSummary.target_context_emphasis.map((emphasis) => (
                          <span key={emphasis} className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
                            {emphasis}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── Stale Artifact Banner ── */}
              {status === 'success' && artifact && isCurrentArtifactStale && (
                <div className="bg-amber-50 border border-amber-300 rounded-lg p-5">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-0.5">
                      <svg className="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <h2 className="text-base font-semibold text-amber-900">This document is out of date</h2>
                      <p className="mt-1 text-sm text-amber-800 leading-relaxed">
                        Accepted changes modified the canonical profile. This document still shows the previously
                        generated version. Regenerate to incorporate your accepted changes.
                      </p>
                      {regenerateError && (
                        <p className="mt-2 text-xs text-red-700">{regenerateError}</p>
                      )}
                      <button
                        type="button"
                        onClick={handleRegenerate}
                        disabled={regenerating}
                        className="mt-3 inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-amber-600 text-white hover:bg-amber-700 border border-amber-700 transition-colors disabled:opacity-60"
                      >
                        {regenerating ? 'Regenerating...' : `Regenerate ${labels.resultHeading}`}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Generated Artifact ── */}
              <div>
                <h2 className="text-base font-semibold text-gray-900 mb-3">{labels.resultHeading}</h2>
                {artifact ? (
                  <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                    <div className="flex items-center justify-end gap-2 mb-4 pb-3 border-b border-gray-100">
                      <button
                        onClick={async () => {
                          try {
                            const docService = DocumentService.getInstance();
                            const blob = await docService.downloadDocx(selectedProfileId, currentArtifactId);
                            const ext = currentArtifactType ? `${currentArtifactType.replace(/_/g, '-')}.docx` : 'document.docx';
                            docService.downloadBlob(blob, ext);
                          } catch (err) {
                            setErrorMessage(err instanceof Error ? err.message : 'Download failed');
                          }
                        }}
                        className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 transition-colors"
                      >
                        Download DOCX
                      </button>
                    </div>
                    <div className="prose prose-sm max-w-none">
                      {renderResume(artifact)}
                    </div>
                  </div>
                ) : (
                  <div className="bg-white border border-gray-200 rounded-lg p-12 shadow-sm flex flex-col items-center justify-center text-gray-400">
                    <svg className="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    <p className="text-sm">{labels.emptyState}</p>
                  </div>
                )}
              </div>

              {/* ── Recommendations ── */}
              <div>
                <h2 className="text-base font-semibold text-gray-900 mb-3">
                  Recommendations{' '}
                  {(profileRecommendations.length > 0 || recommendations.length > 0) && `(${profileRecommendations.length + recommendations.length})`}
                </h2>
                {profileRecommendations.length > 0 || recommendations.length > 0 ? (
                  <div className="space-y-6">
                    {totalRecommendations > 0 && (
                      <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="text-sm font-semibold text-gray-900">Recommendation Progress</h3>
                          <span className="text-xs font-medium text-gray-500">
                            {reviewedCount}/{totalRecommendations} reviewed
                          </span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full overflow-hidden mb-4">
                          <div
                            className="h-full bg-green-500 rounded-full transition-all duration-300"
                            style={{ width: `${reviewProgress}%` }}
                          />
                        </div>
                        <div className="grid grid-cols-4 gap-3 text-center">
                          <div>
                            <p className="text-2xl font-bold text-gray-900">{totalRecommendations}</p>
                            <p className="text-xs text-gray-500 mt-0.5">Total</p>
                          </div>
                          <div>
                            <p className="text-2xl font-bold text-green-600">{reviewedCount}</p>
                            <p className="text-xs text-gray-500 mt-0.5">Completed</p>
                          </div>
                          <div>
                            <p className="text-2xl font-bold text-amber-600">{remainingCount}</p>
                            <p className="text-xs text-gray-500 mt-0.5">Remaining</p>
                          </div>
                          <div>
                            <p className="text-2xl font-bold text-gray-400">{dismissedCount}</p>
                            <p className="text-xs text-gray-500 mt-0.5">Dismissed</p>
                          </div>
                        </div>
                      </div>
                    )}
                    {profileRecommendations.length > 0 && (
                      <div className="space-y-3">
                        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                          Profile Recommendations ({profileRecommendations.length})
                        </h3>
                        {recommendationGroups.map((group) => {
                          const groupTarget = resolveRecommendationTarget(group.recommendations[0]);
                          const groupActionLabel = groupTarget ? SECTION_ACTION_LABELS[groupTarget.section] : null;
                          const noun = groupNoun(group.recommendations);
                          const single = group.recommendations.length === 1;
                          const item = group.recommendations[0];
                          const itemTarget = resolveRecommendationTarget(item);
                          const itemActionLabel = itemTarget ? SECTION_ACTION_LABELS[itemTarget.section] : null;
                          return (
                            <div key={group.key} data-recommendation-group={group.key} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                              <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                  <h4 className="font-semibold text-gray-900">
                                    {group.title}
                                    {!single && (
                                      <span className="ml-2 align-middle inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                                        {group.recommendations.length} {noun}
                                      </span>
                                    )}
                                  </h4>
                                  {groupActionLabel && (
                                    <span className="mt-1.5 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                      {groupActionLabel}
                                    </span>
                                  )}
                                </div>
                                <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
                                  <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${PRIORITY_STYLES[group.priority] ?? 'bg-gray-100 text-gray-700'}`}>
                                    Priority: {capitalizeLevel(group.priority)}
                                  </span>
                                  <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${IMPACT_STYLES[group.impact] ?? 'bg-gray-100 text-gray-700'}`}>
                                    Impact: {capitalizeLevel(group.impact)}
                                  </span>
                                </div>
                              </div>
                              <p className="mt-2 text-sm text-gray-700 leading-relaxed">
                                {single
                                  ? item.reason
                                  : `CareerOS found this issue in ${group.recommendations.length} ${noun}.`}
                              </p>
                              {single ? (
                                <div data-recommendation-id={item.id} className="mt-3 border-t border-gray-100 pt-2.5">
                                  <div className="flex items-start justify-between gap-3">
                                    <p className="min-w-0 text-sm font-medium text-gray-900">
                                      {elementDisplayName(item, selectedProfile)}
                                    </p>
                                    <div className="flex shrink-0 flex-wrap items-center gap-1.5">
                                      {canResolve(item) && (
                                        <button
                                          onClick={() => toggleResolutionPanel(item)}
                                          className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
                                        >
                                          {openResolutionId === item.id ? 'Close panel' : 'Resolve'}
                                        </button>
                                      )}
                                      {itemActionLabel && (
                                        <button
                                          onClick={() => handleGoToSection(item)}
                                          className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                                        >
                                          Go to section
                                        </button>
                                      )}
                                      {reviewedIds.has(item.id) ? (
                                        <button
                                          onClick={() => toggleReviewed(item.id)}
                                          className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-green-100 text-green-800 hover:bg-green-200 border border-green-200 transition-colors"
                                        >
                                          Reviewed — undo
                                        </button>
                                      ) : (
                                        <button
                                          onClick={() => toggleReviewed(item.id)}
                                          className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
                                        >
                                          Mark as reviewed
                                        </button>
                                      )}
                                      {dismissedIds.has(item.id) ? (
                                        <button
                                          onClick={() => toggleDismissed(item.id)}
                                          className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-gray-200 text-gray-600 hover:bg-gray-300 transition-colors"
                                        >
                                          Dismissed — restore
                                        </button>
                                      ) : (
                                        <button
                                          onClick={() => toggleDismissed(item.id)}
                                          className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium border border-gray-300 text-gray-600 hover:bg-gray-50 transition-colors"
                                        >
                                          Dismiss
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                  {renderRecommendationDetails(item)}
                                  {openResolutionId === item.id && renderResolutionPanel(item)}
                                </div>
                              ) : (
                                <details className="mt-3 border-t border-gray-100 pt-2">
                                  <summary className="cursor-pointer select-none text-xs font-semibold uppercase tracking-wide text-gray-500 hover:text-gray-700">
                                    View {group.recommendations.length} affected {noun}
                                  </summary>
                                  <div className="mt-1 divide-y divide-gray-100">
                                    {group.recommendations.map((rec) => {
                                      const target = resolveRecommendationTarget(rec);
                                      const actionLabel = target ? SECTION_ACTION_LABELS[target.section] : null;
                                      const reviewed = reviewedIds.has(rec.id);
                                      const dismissed = dismissedIds.has(rec.id);
                                      return (
                                        <div key={rec.id} data-recommendation-id={rec.id} className="py-2.5">
                                          <div className="flex items-start justify-between gap-3">
                                            <div className="min-w-0">
                                              <p className="text-sm font-medium text-gray-900">
                                                {elementDisplayName(rec, selectedProfile)}
                                              </p>
                                              <p className="mt-0.5 text-xs text-gray-500 leading-relaxed">{rec.reason}</p>
                                              {reviewed && (
                                                <span className="mt-1 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                                  Reviewed
                                                </span>
                                              )}
                                              {dismissed && (
                                                <span className="mt-1 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-600">
                                                  Dismissed
                                                </span>
                                              )}
                                            </div>
                                            <div className="flex shrink-0 flex-wrap items-center gap-1.5">
                                              {canResolve(rec) && (
                                                <button
                                                  onClick={() => toggleResolutionPanel(rec)}
                                                  className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
                                                >
                                                  {openResolutionId === rec.id ? 'Close panel' : 'Resolve'}
                                                </button>
                                              )}
                                              {actionLabel && (
                                                <button
                                                  onClick={() => handleGoToSection(rec)}
                                                  className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                                                >
                                                  Go to section
                                                </button>
                                              )}
                                              {reviewed ? (
                                                <button
                                                  onClick={() => toggleReviewed(rec.id)}
                                                  className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-green-100 text-green-800 hover:bg-green-200 border border-green-200 transition-colors"
                                                >
                                                  Reviewed — undo
                                                </button>
                                              ) : (
                                                <button
                                                  onClick={() => toggleReviewed(rec.id)}
                                                  className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
                                                >
                                                  Mark as reviewed
                                                </button>
                                              )}
                                              {dismissed ? (
                                                <button
                                                  onClick={() => toggleDismissed(rec.id)}
                                                  className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-gray-200 text-gray-600 hover:bg-gray-300 transition-colors"
                                                >
                                                  Dismissed — restore
                                                </button>
                                              ) : (
                                                <button
                                                  onClick={() => toggleDismissed(rec.id)}
                                                  className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium border border-gray-300 text-gray-600 hover:bg-gray-50 transition-colors"
                                                >
                                                  Dismiss
                                                </button>
                                              )}
                                            </div>
                                          </div>
                                          {renderRecommendationDetails(rec)}
                                          {openResolutionId === rec.id && renderResolutionPanel(rec)}
                                        </div>
                                      );
                                    })}
                                  </div>
                                </details>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {recommendations.length > 0 && (
                      <div className="space-y-3">
                        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                          Optimization Recommendations ({recommendations.length})
                        </h3>
                        {recommendations.map((rec) => (
                          <div key={rec.id} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                            <div className="flex items-start justify-between">
                              <h4 className="font-semibold text-gray-900">{rec.displayName}</h4>
                              {getRecommendationConfidence(rec) !== null && (
                                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                                  {getRecommendationConfidence(rec)}% match
                                </span>
                              )}
                            </div>
                            <div className="mt-2 text-sm text-gray-600">
                              <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 mr-2">
                                {rec.type}
                              </span>
                              <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                                {rec.operation}
                              </span>
                            </div>
                            {getRecommendationReason(rec) && (
                              <p className="mt-2 text-sm text-gray-700">{getRecommendationReason(rec)}</p>
                            )}
                            {getRecommendationImpact(rec) && (
                              <p className="mt-1 text-sm text-gray-600 italic">{getRecommendationImpact(rec)}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-white border border-gray-200 rounded-lg p-12 shadow-sm flex flex-col items-center justify-center text-gray-400">
                    <svg className="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                    </svg>
                    <p className="text-sm">
                      {recommendationsLoading ? 'Analyzing profile recommendations...' :
                       status === 'analyzing' || status === 'generating' ? 'Analyzing recommendations...' :
                       status === 'success' && optimizationStatus === 'already_complete' ? labels.completeMessage :
                       status === 'success' && optimizationStatus === 'no_matches' ? 'No additional evidence found' :
                       'No recommendations — your profile looks strong'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
