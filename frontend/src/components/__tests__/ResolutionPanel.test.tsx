import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ResolutionPanel from '../ResolutionPanel';
import type { ProfileDetails, ResolutionPayload, UnifiedRecommendation } from '../../types';

const PROFILE: ProfileDetails = {
  id: 'test-profile',
  person: { firstName: 'Jane', lastName: 'Doe', headline: 'Engineer', city: null, country: null, languages: [] },
  artifacts: [],
  summary: null,
  importedAt: '2026-01-01',
  professionalSummaries: [],
  experiences: [
    { id: 'exp-1', title: 'Software Engineer', organization: 'Acme Inc', dateRange: null, scope: 'Built stuff.', engagementType: '' },
    { id: 'exp-2', title: 'Intern', organization: 'Startup', dateRange: null, scope: 'Learned.', engagementType: '' },
  ],
  skills: [
    { id: 'skill-1', name: 'Python', category: '', description: '' },
    { id: 'skill-2', name: 'Docker', category: '', description: '' },
    { id: 'skill-3', name: 'Kubernetes', category: '', description: '' },
  ],
  education: [],
  certifications: [],
  projects: [{ id: 'proj-1', name: 'My Project', description: 'A cool project.' }],
};

const TECHNOLOGIES = ['python', 'docker', 'kubernetes', 'terraform', 'aws'];

function makeRec(ruleId: string, overrides: Partial<UnifiedRecommendation> = {}): UnifiedRecommendation {
  return {
    id: 'rec-1',
    source: 'profile_quality',
    rule_id: ruleId,
    element_id: 'proj-1',
    element_type: 'project',
    title: 'A recommendation',
    reason: 'This area needs improvement.',
    suggested_action: 'Try adding more details.',
    resolution_type: 'auto',
    evidence_refs: ['proj-1.details', 'proj-1.metrics'],
    priority: 'high',
    estimated_impact: 'high',
    confidence: 'high',
    jd_match_score: null,
    context_match_score: null,
    weighted_total: null,
    ...overrides,
  };
}

function renderPanel(
  rec: UnifiedRecommendation,
  onApply = vi.fn(),
  onClose = vi.fn(),
) {
  return render(
    <ResolutionPanel
      rec={rec}
      profile={PROFILE}
      technologies={TECHNOLOGIES}
      onApply={onApply}
      onClose={onClose}
    />,
  );
}

describe('ResolutionPanel', () => {
  it('renders title, reason, suggested action, and evidence for any rule', () => {
    renderPanel(makeRec('recommendation_add_skills_to_project'));
    expect(screen.getByText('Resolve recommendation')).toBeTruthy();
    expect(screen.getByText('A recommendation')).toBeTruthy();
    expect(screen.getByText('This area needs improvement.')).toBeTruthy();
    expect(screen.getByText('Try adding more details.')).toBeTruthy();
    expect(screen.getAllByTestId('resolution-evidence-ref').length).toBe(2);
  });

  describe('ProjectWithoutSkillsRule', () => {
    const rec = makeRec('recommendation_add_skills_to_project', { element_id: 'proj-1' });

    it('renders skill checklist and experience checklist', () => {
      renderPanel(rec);
      expect(screen.getByText('Skills')).toBeTruthy();
      expect(screen.getByText('Python')).toBeTruthy();
      expect(screen.getByText('Related experiences')).toBeTruthy();
      expect(screen.getByText(/Software Engineer/)).toBeTruthy();
    });

    it('Apply is disabled when nothing is selected', () => {
      renderPanel(rec);
      const apply = screen.getByTestId('resolution-apply');
      expect((apply as HTMLButtonElement).disabled).toBe(true);
    });

    it('Apply is enabled when at least one skill is selected', () => {
      renderPanel(rec);
      fireEvent.click(screen.getByLabelText('Python'));
      const apply = screen.getByTestId('resolution-apply');
      expect((apply as HTMLButtonElement).disabled).toBe(false);
    });

    it('calls onApply with correct payload on Apply', async () => {
      const onApply = vi.fn(async (_: ResolutionPayload) => {});
      renderPanel(rec, onApply);
      fireEvent.click(screen.getByLabelText('Python'));
      fireEvent.click(screen.getByLabelText('Software Engineer — Acme Inc'));
      fireEvent.click(screen.getByTestId('resolution-apply'));
      await waitFor(() => {
        expect(onApply).toHaveBeenCalledWith({
          triggeredRule: 'ProjectWithoutSkillsRule',
          elementId: 'proj-1',
          skillIds: ['skill-1'],
          experienceIds: ['exp-1'],
          technologies: [],
          achievementStatement: '',
        });
      });
    });
  });

  describe('ExperienceNoTechnologiesRule', () => {
    const rec = makeRec('recommendation_add_technologies', { element_id: 'exp-1', element_type: 'experience' });

    it('renders technology filter and checklist', () => {
      renderPanel(rec);
      expect(screen.getByPlaceholderText('Filter technologies...')).toBeTruthy();
      expect(screen.getByText('python')).toBeTruthy();
      expect(screen.getByText('docker')).toBeTruthy();
    });

    it('Apply is disabled when no technologies are selected', () => {
      renderPanel(rec);
      const apply = screen.getByTestId('resolution-apply');
      expect((apply as HTMLButtonElement).disabled).toBe(true);
    });

    it('calls onApply with selected technologies', async () => {
      const onApply = vi.fn(async (_: ResolutionPayload) => {});
      renderPanel(rec, onApply);
      fireEvent.click(screen.getByLabelText('python'));
      fireEvent.click(screen.getByLabelText('docker'));
      fireEvent.click(screen.getByTestId('resolution-apply'));
      await waitFor(() => {
        expect(onApply).toHaveBeenCalledWith({
          triggeredRule: 'ExperienceNoTechnologiesRule',
          elementId: 'exp-1',
          skillIds: [],
          experienceIds: [],
          technologies: ['python', 'docker'],
          achievementStatement: '',
        });
      });
    });
  });

  describe('SkillWithoutExperienceRule', () => {
    const rec = makeRec('recommendation_show_skill_in_experience', { element_id: 'skill-1', element_type: 'skill' });

    it('renders experience checklist', () => {
      renderPanel(rec);
      expect(screen.getByText(/Software Engineer/)).toBeTruthy();
      expect(screen.getByText(/Intern/)).toBeTruthy();
    });

    it('calls onApply with selected experiences', async () => {
      const onApply = vi.fn(async (_: ResolutionPayload) => {});
      renderPanel(rec, onApply);
      fireEvent.click(screen.getByLabelText('Software Engineer — Acme Inc'));
      fireEvent.click(screen.getByTestId('resolution-apply'));
      await waitFor(() => {
        expect(onApply).toHaveBeenCalledWith({
          triggeredRule: 'SkillWithoutExperienceRule',
          elementId: 'skill-1',
          skillIds: [],
          experienceIds: ['exp-1'],
          technologies: [],
          achievementStatement: '',
        });
      });
    });
  });

  describe('NoMeasurableAchievementRule', () => {
    const rec = makeRec('recommendation_add_measurable_achievement', { element_id: 'exp-1', element_type: 'experience' });

    it('renders textarea and optional skills checklist', () => {
      renderPanel(rec);
      expect(screen.getByPlaceholderText('e.g. Reduced deployment time by 60%')).toBeTruthy();
      expect(screen.getByText('Related skills (optional)')).toBeTruthy();
      expect(screen.getByText('Python')).toBeTruthy();
    });

    it('Apply is disabled when statement is not measurable', () => {
      renderPanel(rec);
      const apply = screen.getByTestId('resolution-apply');
      expect((apply as HTMLButtonElement).disabled).toBe(true);
      fireEvent.change(screen.getByPlaceholderText('e.g. Reduced deployment time by 60%'), { target: { value: 'Did some work' } });
      expect((apply as HTMLButtonElement).disabled).toBe(true);
    });

    it('Apply is enabled with a number in the statement', () => {
      renderPanel(rec);
      fireEvent.change(screen.getByPlaceholderText('e.g. Reduced deployment time by 60%'), { target: { value: 'reduced incidents by 40%' } });
      const apply = screen.getByTestId('resolution-apply');
      expect((apply as HTMLButtonElement).disabled).toBe(false);
    });

    it('Apply is enabled with a business outcome word but no number', () => {
      renderPanel(rec);
      fireEvent.change(screen.getByPlaceholderText('e.g. Reduced deployment time by 60%'), { target: { value: 'improved efficiency across teams' } });
      const apply = screen.getByTestId('resolution-apply');
      expect((apply as HTMLButtonElement).disabled).toBe(false);
    });

    it('shows measurability hint when statement is not yet measurable', () => {
      renderPanel(rec);
      fireEvent.change(screen.getByPlaceholderText('e.g. Reduced deployment time by 60%'), { target: { value: 'Did some work' } });
      expect(screen.getByText(/Add a number/)).toBeTruthy();
    });

    it('calls onApply with achievement statement and optional skills', async () => {
      const onApply = vi.fn(async (_: ResolutionPayload) => {});
      renderPanel(rec, onApply);
      fireEvent.change(screen.getByPlaceholderText('e.g. Reduced deployment time by 60%'), { target: { value: 'Reduced deployment time by 60%' } });
      fireEvent.click(screen.getByLabelText('Python'));
      fireEvent.click(screen.getByTestId('resolution-apply'));
      await waitFor(() => {
        expect(onApply).toHaveBeenCalledWith({
          triggeredRule: 'NoMeasurableAchievementRule',
          elementId: 'exp-1',
          skillIds: ['skill-1'],
          experienceIds: [],
          technologies: [],
          achievementStatement: 'Reduced deployment time by 60%',
        });
      });
    });
  });

  it('shows error when onApply rejects', async () => {
    const onApply = vi.fn(async (_: ResolutionPayload) => {
      throw new Error('Server error');
    });
    renderPanel(
      makeRec('recommendation_add_measurable_achievement', { element_id: 'exp-1', element_type: 'experience' }),
      onApply,
    );
    fireEvent.change(screen.getByPlaceholderText('e.g. Reduced deployment time by 60%'), { target: { value: 'Reduced incidents by 40%' } });
    fireEvent.click(screen.getByTestId('resolution-apply'));
    await waitFor(() => {
      expect(screen.getByTestId('resolution-error').textContent).toBe('Server error');
    });
  });

  it('shows "Applying..." while applying', async () => {
    let resolveApply: (value: void | PromiseLike<void>) => void;
    const onApply = vi.fn(
      () => new Promise<void>((resolve) => { resolveApply = resolve; }),
    );
    renderPanel(
      makeRec('recommendation_add_technologies', { element_id: 'exp-1', element_type: 'experience' }),
      onApply,
    );
    fireEvent.click(screen.getByLabelText('python'));
    fireEvent.click(screen.getByTestId('resolution-apply'));
    expect(screen.getByText('Applying...')).toBeTruthy();
    resolveApply!(undefined);
    await waitFor(() => {
      expect(screen.queryByText('Applying...')).toBeNull();
    });
  });

  it('calls onClose when Cancel is clicked', () => {
    const onClose = vi.fn();
    renderPanel(makeRec('recommendation_add_skills_to_project'), vi.fn(), onClose);
    fireEvent.click(screen.getByTestId('resolution-cancel'));
    expect(onClose).toHaveBeenCalledOnce();
  });
});