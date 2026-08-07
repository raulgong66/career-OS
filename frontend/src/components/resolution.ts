import type { ResolutionPayload, UnifiedRecommendation } from '../types';

export const RESOLVABLE_TRIGGERED_RULES = [
  'ProjectWithoutSkillsRule',
  'ExperienceNoTechnologiesRule',
  'SkillWithoutExperienceRule',
  'NoMeasurableAchievementRule',
] as const;

export const RULE_ID_TO_TRIGGERED_RULE: Record<string, string> = {
  recommendation_add_skills_to_project: 'ProjectWithoutSkillsRule',
  recommendation_add_technologies: 'ExperienceNoTechnologiesRule',
  recommendation_show_skill_in_experience: 'SkillWithoutExperienceRule',
  recommendation_add_measurable_achievement: 'NoMeasurableAchievementRule',
};

export function isResolvableRecommendation(rec: UnifiedRecommendation): boolean {
  return rec.rule_id in RULE_ID_TO_TRIGGERED_RULE;
}

export function buildResolutionPayload(
  rec: UnifiedRecommendation,
  selections: {
    skillIds?: string[];
    experienceIds?: string[];
    technologies?: string[];
    achievementStatement?: string;
  },
): ResolutionPayload {
  return {
    triggeredRule: RULE_ID_TO_TRIGGERED_RULE[rec.rule_id],
    elementId: rec.element_id,
    skillIds: selections.skillIds ?? [],
    experienceIds: selections.experienceIds ?? [],
    technologies: selections.technologies ?? [],
    achievementStatement: selections.achievementStatement ?? '',
  };
}

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

export function isMeasurableStatement(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) return false;
  if (NUMBER_PATTERN.test(trimmed)) return true;
  const lower = trimmed.toLowerCase();
  return [...BUSINESS_OUTCOME_WORDS].some((word) => {
    const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`\\b${escaped}\\b`).test(lower);
  });
}
