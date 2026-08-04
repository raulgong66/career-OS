import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ImprovementQueue from '../ImprovementQueue';
import type { UnifiedRecommendation } from '../../types';

const recommendations: UnifiedRecommendation[] = [
  {
    id: 'rec-1',
    source: 'profile_quality',
    rule_id: 'quality:achievement-measurability',
    element_id: 'exp-1',
    element_type: 'experience',
    title: 'Strengthen quantified impact in work experience',
    reason: '3 experiences lack metrics.',
    suggested_action: 'Add numbers to outcomes.',
    resolution_type: 'guided',
    evidence_refs: ['exp-1.details'],
    priority: 'high',
    estimated_impact: 'high',
    confidence: 'medium',
    jd_match_score: null,
    context_match_score: null,
    weighted_total: null,
  },
  {
    id: 'rec-2',
    source: 'optimization',
    rule_id: 'quality:achievement-measurability',
    element_id: 'exp-2',
    element_type: 'experience',
    title: 'Strengthen quantified impact in work experience',
    reason: 'Missing metric.',
    suggested_action: 'Quantify the outcome.',
    resolution_type: 'auto',
    evidence_refs: ['exp-2.details'],
    priority: 'medium',
    estimated_impact: 'medium',
    confidence: 'high',
    jd_match_score: 72,
    context_match_score: 80,
    weighted_total: 76,
  },
  {
    id: 'rec-3',
    source: 'profile_quality',
    rule_id: 'quality:skill-deduplication',
    element_id: 'skill-1',
    element_type: 'skill',
    title: 'Remove duplicate skills',
    reason: 'Similar skills appear twice.',
    suggested_action: 'Deduplicate.',
    resolution_type: 'auto',
    evidence_refs: ['skill-1.details'],
    priority: 'low',
    estimated_impact: 'low',
    confidence: 'high',
    jd_match_score: null,
    context_match_score: null,
    weighted_total: null,
  },
];

const emptyFilters = { priority: '', resolutionType: '' } as const;

describe('ImprovementQueue', () => {
  it('groups cards by rule and shows one group header', () => {
    render(
      <ImprovementQueue
        recommendations={recommendations}
        filters={emptyFilters}
        onFilterChange={vi.fn()}
      />,
    );

    const titles = screen.getAllByText('Strengthen quantified impact in work experience');
    expect(titles.length).toBe(3);
    expect(screen.getAllByText('Remove duplicate skills').length).toBe(2);
    expect(screen.getAllByTestId('priority-badge')).toHaveLength(3);
    expect(screen.getAllByTestId('resolution-badge')).toHaveLength(3);
    expect(screen.getByText('2')).toBeTruthy();
  });

  it('renders priority and resolution badges per card', () => {
    render(
      <ImprovementQueue
        recommendations={recommendations}
        filters={emptyFilters}
        onFilterChange={vi.fn()}
      />,
    );

    const priorityBadges = screen.getAllByTestId('priority-badge');
    expect(priorityBadges.map((badge) => badge.textContent)).toEqual(['High', 'Medium', 'Low']);
    const resolutionBadges = screen.getAllByTestId('resolution-badge');
    expect(resolutionBadges.map((badge) => badge.textContent)).toEqual(['guided', 'auto', 'auto']);
  });

  it('shows recommendation count', () => {
    render(
      <ImprovementQueue
        recommendations={recommendations}
        filters={emptyFilters}
        onFilterChange={vi.fn()}
      />,
    );

    expect(screen.getByText('3 recommendations')).toBeTruthy();
  });

  it('expands details showing reason, action, and evidence refs', () => {
    render(
      <ImprovementQueue
        recommendations={recommendations}
        filters={emptyFilters}
        onFilterChange={vi.fn()}
      />,
    );

    const detailsElements = document.querySelectorAll('details');
    expect(detailsElements.length).toBe(3);

    const summaries = screen.getAllByText('Details');
    expect(summaries.length).toBe(3);

    const first = detailsElements[0];
    if (!(first instanceof HTMLDetailsElement)) {
      throw new Error('expected details element');
    }
    first.open = true;

    expect(screen.getByText('3 experiences lack metrics.')).toBeTruthy();
    expect(screen.getByText('Add numbers to outcomes.')).toBeTruthy();
    expect(screen.getAllByTestId('evidence-ref').length).toBeGreaterThan(0);
  });

  it('calls onFilterChange when priority filter changes', () => {
    const onFilterChange = vi.fn();
    render(
      <ImprovementQueue
        recommendations={recommendations}
        filters={emptyFilters}
        onFilterChange={onFilterChange}
      />,
    );

    fireEvent.change(screen.getByLabelText('Priority'), { target: { value: 'high' } });
    expect(onFilterChange).toHaveBeenCalledWith({ priority: 'high', resolutionType: '' });
  });

  it('calls onFilterChange when resolution filter changes', () => {
    const onFilterChange = vi.fn();
    render(
      <ImprovementQueue
        recommendations={recommendations}
        filters={emptyFilters}
        onFilterChange={onFilterChange}
      />,
    );

    fireEvent.change(screen.getByLabelText('Resolution'), { target: { value: 'auto' } });
    expect(onFilterChange).toHaveBeenCalledWith({ priority: '', resolutionType: 'auto' });
  });

  it('shows empty state when no recommendations', () => {
    render(
      <ImprovementQueue recommendations={[]} filters={emptyFilters} onFilterChange={vi.fn()} />,
    );

    expect(screen.getByTestId('queue-empty').textContent).toContain(
      'No pending improvements',
    );
  });
});
