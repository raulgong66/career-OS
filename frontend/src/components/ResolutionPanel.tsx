import { useEffect, useRef, useState } from 'react';
import type { ProfileDetails, ResolutionPayload, UnifiedRecommendation } from '../types';
import {
  buildResolutionPayload,
  isMeasurableStatement,
  RULE_ID_TO_TRIGGERED_RULE,
} from './resolution';

export interface ResolutionPanelProps {
  rec: UnifiedRecommendation;
  profile: ProfileDetails;
  technologies: string[];
  onApply: (payload: ResolutionPayload) => Promise<void>;
  onClose: () => void;
}

export default function ResolutionPanel({
  rec,
  profile,
  technologies,
  onApply,
  onClose,
}: ResolutionPanelProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const triggeredRule = RULE_ID_TO_TRIGGERED_RULE[rec.rule_id];
  const [selectedSkillIds, setSelectedSkillIds] = useState<Set<string>>(new Set());
  const [selectedExperienceIds, setSelectedExperienceIds] = useState<Set<string>>(new Set());
  const [selectedTechnologies, setSelectedTechnologies] = useState<Set<string>>(new Set());
  const [techQuery, setTechQuery] = useState('');
  const [achievementStatement, setAchievementStatement] = useState('');
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState('');
  const [highlighted, setHighlighted] = useState(false);

  const toggleInSet = (set: Set<string>, setter: (next: Set<string>) => void) => (value: string) => {
    const next = new Set(set);
    if (next.has(value)) {
      next.delete(value);
    } else {
      next.add(value);
    }
    setter(next);
  };

  const toggleSkill = toggleInSet(selectedSkillIds, setSelectedSkillIds);
  const toggleExperience = toggleInSet(selectedExperienceIds, setSelectedExperienceIds);
  const toggleTechnology = toggleInSet(selectedTechnologies, setSelectedTechnologies);

  useEffect(() => {
    const node = rootRef.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
    const fullyVisible = rect.top >= 0 && rect.bottom <= viewportHeight;
    if (!fullyVisible) {
      node.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
    }
    node.focus?.({ preventScroll: true });
    setHighlighted(true);
    const timer = setTimeout(() => setHighlighted(false), 1500);
    return () => clearTimeout(timer);
  }, []);

  const filteredTechnologies = technologies.filter((keyword) =>
    keyword.toLowerCase().includes(techQuery.trim().toLowerCase()),
  );

  const nothingSelected =
    triggeredRule === 'ExperienceNoTechnologiesRule'
      ? selectedTechnologies.size === 0
      : triggeredRule === 'SkillWithoutExperienceRule'
        ? selectedExperienceIds.size === 0
        : triggeredRule === 'NoMeasurableAchievementRule'
          ? !isMeasurableStatement(achievementStatement)
          : selectedSkillIds.size === 0 && selectedExperienceIds.size === 0;

  const handleApply = async () => {
    setApplying(true);
    setError('');
    try {
      await onApply(
        buildResolutionPayload(rec, {
          skillIds: [...selectedSkillIds],
          experienceIds: [...selectedExperienceIds],
          technologies: [...selectedTechnologies],
          achievementStatement,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply changes');
    } finally {
      setApplying(false);
    }
  };

  return (
    <div
      className={`border rounded-lg p-4 transition-shadow duration-500 ${
        highlighted
          ? 'border-emerald-400 bg-emerald-50 shadow-lg ring-2 ring-emerald-300'
          : 'border-emerald-200 bg-emerald-50 shadow-none'
      }`}
      data-testid="resolution-panel"
      tabIndex={-1}
      ref={rootRef}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-emerald-900">Resolve recommendation</p>
        <button
          onClick={onClose}
          aria-label="Close resolution panel"
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ✕
        </button>
      </div>
      <p className="mt-1 text-sm font-medium text-gray-900">{rec.title}</p>

      {rec.reason && (
        <p className="mt-2 text-sm leading-relaxed text-gray-700">{rec.reason}</p>
      )}

      {rec.suggested_action && (
        <div className="mt-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Suggested action</p>
          <p className="mt-1 text-sm leading-relaxed text-gray-800">{rec.suggested_action}</p>
        </div>
      )}

      {rec.evidence_refs.length > 0 && (
        <div className="mt-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Evidence</p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {rec.evidence_refs.map((ref) => (
              <span
                key={ref}
                className="inline-flex items-center px-2 py-0.5 rounded bg-white text-xs font-medium text-gray-700"
                data-testid="resolution-evidence-ref"
              >
                {ref}
              </span>
            ))}
          </div>
        </div>
      )}

      {triggeredRule === 'ProjectWithoutSkillsRule' && (
        <>
          <p className="mt-3 text-sm text-gray-700">
            Tag this project with the skills it demonstrates. You can also link related experiences.
          </p>
          <p className="mt-2 text-xs font-semibold text-gray-600 uppercase tracking-wide">Skills</p>
          <ul className="mt-1 max-h-40 space-y-1 overflow-y-auto">
            {profile.skills.map((skill) => (
              <li key={skill.id} className="flex items-start text-sm text-gray-700">
                <input
                  id={`${rec.id}-skill-${skill.id}`}
                  type="checkbox"
                  checked={selectedSkillIds.has(skill.id)}
                  onChange={() => toggleSkill(skill.id)}
                  className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 rounded-sm border-gray-400 text-emerald-600"
                />
                <label htmlFor={`${rec.id}-skill-${skill.id}`} className="ml-2 cursor-pointer select-none">{skill.name}</label>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs font-semibold text-gray-600 uppercase tracking-wide">Related experiences</p>
          <ul className="mt-1 max-h-40 space-y-1 overflow-y-auto">
            {profile.experiences.map((exp) => (
              <li key={exp.id} className="flex items-start text-sm text-gray-700">
                <input
                  id={`${rec.id}-experience-${exp.id}`}
                  type="checkbox"
                  checked={selectedExperienceIds.has(exp.id)}
                  onChange={() => toggleExperience(exp.id)}
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

      {triggeredRule === 'ExperienceNoTechnologiesRule' && (
        <>
          <p className="mt-3 text-sm text-gray-700">
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
            {filteredTechnologies.length > 0 ? (
              filteredTechnologies.map((keyword) => (
                <li key={keyword} className="flex items-start text-sm text-gray-700">
                  <input
                    id={`${rec.id}-tech-${keyword}`}
                    type="checkbox"
                    checked={selectedTechnologies.has(keyword)}
                    onChange={() => toggleTechnology(keyword)}
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

      {triggeredRule === 'SkillWithoutExperienceRule' && (
        <>
          <p className="mt-3 text-sm text-gray-700">
            Choose the experience entries that demonstrate this skill.
          </p>
          <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto">
            {profile.experiences.map((exp) => (
              <li key={exp.id} className="flex items-start text-sm text-gray-700">
                <input
                  id={`${rec.id}-experience-${exp.id}`}
                  type="checkbox"
                  checked={selectedExperienceIds.has(exp.id)}
                  onChange={() => toggleExperience(exp.id)}
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

      {triggeredRule === 'NoMeasurableAchievementRule' && (
        <>
          <p className="mt-3 text-sm text-gray-700">
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
              {profile.skills.map((skill) => (
                <li key={skill.id} className="flex items-start text-sm text-gray-700">
                  <input
                    id={`${rec.id}-achievement-skill-${skill.id}`}
                    type="checkbox"
                    checked={selectedSkillIds.has(skill.id)}
                    onChange={() => toggleSkill(skill.id)}
                    className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 rounded-sm border-gray-400 text-emerald-600"
                  />
                  <label htmlFor={`${rec.id}-achievement-skill-${skill.id}`} className="ml-2 cursor-pointer select-none">{skill.name}</label>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      {error && (
        <p className="mt-2 text-sm text-red-600" data-testid="resolution-error">{error}</p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          onClick={() => void handleApply()}
          disabled={applying || nothingSelected}
          className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          data-testid="resolution-apply"
        >
          {applying ? 'Applying...' : 'Apply to profile'}
        </button>
        <button
          onClick={onClose}
          className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
          data-testid="resolution-cancel"
        >
          Cancel
        </button>
        <span className="text-xs text-gray-400">Writes canonical profile changes</span>
      </div>
    </div>
  );
}
