export const DIMENSION_LABELS: Record<string, string> = {
  achievement_measurability: 'Achievement Measurability',
  skill_evidence_coverage: 'Skill Evidence Coverage',
  technology_presence: 'Technology Presence',
  summary_quality: 'Summary Quality',
  skill_deduplication: 'Skill Deduplication',
  business_outcome_language: 'Business Outcome Language',
  certification_utilization: 'Certification Utilization',
  project_skill_linkage: 'Project Skill Linkage',
};

export function dimensionLabel(name: string): string {
  return DIMENSION_LABELS[name] ?? name;
}

export function healthCategory(score: number): string {
  if (score >= 80) return 'Strong';
  if (score >= 60) return 'Solid';
  if (score >= 40) return 'Developing';
  return 'Needs attention';
}

export function capitalizeLevel(level: string): string {
  return level ? level.charAt(0).toUpperCase() + level.slice(1) : level;
}
