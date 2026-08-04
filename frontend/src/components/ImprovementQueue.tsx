import type { QueueFilters, RecommendationPriority, UnifiedRecommendation } from '../types';
import RecommendationCard from './RecommendationCard';
import { capitalizeLevel } from './healthDisplay';

interface ImprovementQueueProps {
  recommendations: UnifiedRecommendation[];
  filters: QueueFilters;
  onFilterChange: (filters: QueueFilters) => void;
}

const PRIORITY_RANK: Record<RecommendationPriority, number> = {
  high: 3,
  medium: 2,
  low: 1,
};

const PRIORITY_STYLES: Record<RecommendationPriority, string> = {
  high: 'bg-red-100 text-red-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-gray-100 text-gray-700',
};

interface RecommendationGroup {
  ruleId: string;
  title: string;
  priority: RecommendationPriority;
  recommendations: UnifiedRecommendation[];
}

function groupRecommendations(items: UnifiedRecommendation[]): RecommendationGroup[] {
  const groups = new Map<string, RecommendationGroup>();
  for (const rec of items) {
    let group = groups.get(rec.rule_id);
    if (!group) {
      group = {
        ruleId: rec.rule_id,
        title: rec.title,
        priority: rec.priority,
        recommendations: [],
      };
      groups.set(rec.rule_id, group);
    }
    if (PRIORITY_RANK[rec.priority] > PRIORITY_RANK[group.priority]) {
      group.priority = rec.priority;
    }
    group.recommendations.push(rec);
  }
  return [...groups.values()];
}

const FILTER_OPTIONS: Array<{ value: QueueFilters['priority'] | QueueFilters['resolutionType']; label: string }> = [
  { value: '', label: 'All' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const RESOLUTION_OPTIONS: Array<{ value: QueueFilters['resolutionType']; label: string }> = [
  { value: '', label: 'All' },
  { value: 'auto', label: 'Auto' },
  { value: 'guided', label: 'Guided' },
  { value: 'none', label: 'None' },
];

export default function ImprovementQueue({
  recommendations,
  filters,
  onFilterChange,
}: ImprovementQueueProps) {
  const groups = groupRecommendations(recommendations);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <label htmlFor="queue-priority-filter" className="text-xs font-medium text-gray-600">Priority</label>
          <select
            id="queue-priority-filter"
            value={filters.priority}
            onChange={(event) =>
              onFilterChange({ ...filters, priority: event.target.value as QueueFilters['priority'] })
            }
            className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs text-gray-800 focus:border-blue-500 focus:outline-none"
          >
            {FILTER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label htmlFor="queue-resolution-filter" className="text-xs font-medium text-gray-600">Resolution</label>
          <select
            id="queue-resolution-filter"
            value={filters.resolutionType}
            onChange={(event) =>
              onFilterChange({
                ...filters,
                resolutionType: event.target.value as QueueFilters['resolutionType'],
              })
            }
            className="rounded-md border border-gray-300 bg-white px-2 py-1 text-xs text-gray-800 focus:border-blue-500 focus:outline-none"
          >
            {RESOLUTION_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <span className="ml-auto text-xs text-gray-400">
          {recommendations.length} recommendation{recommendations.length !== 1 ? 's' : ''}
        </span>
      </div>

      {recommendations.length === 0 ? (
        <p className="text-sm text-gray-400 italic" data-testid="queue-empty">
          No pending improvements. Your profile is in great shape.
        </p>
      ) : (
        <div className="space-y-4">
          {groups.map((group) => (
            <div key={group.ruleId}>
              <div className="mb-1.5 flex items-center gap-2">
                <p className="text-sm font-semibold text-gray-900">{group.title}</p>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${PRIORITY_STYLES[group.priority]}`}
                >
                  {capitalizeLevel(group.priority)}
                </span>
                <span className="text-xs text-gray-400">{group.recommendations.length}</span>
              </div>
              <div className="space-y-2">
                {group.recommendations.map((recommendation) => (
                  <RecommendationCard key={recommendation.id} recommendation={recommendation} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
