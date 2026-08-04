import type { UnifiedRecommendation } from '../types';
import { capitalizeLevel } from './healthDisplay';

const PRIORITY_STYLES: Record<UnifiedRecommendation['priority'], string> = {
  high: 'bg-red-100 text-red-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-gray-100 text-gray-700',
};

const RESOLUTION_STYLES: Record<UnifiedRecommendation['resolution_type'], string> = {
  auto: 'bg-emerald-100 text-emerald-800',
  guided: 'bg-blue-100 text-blue-800',
  none: 'bg-gray-100 text-gray-600',
};

interface RecommendationCardProps {
  recommendation: UnifiedRecommendation;
}

export default function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const { title, priority, resolution_type, reason, suggested_action, element_type, element_id, evidence_refs } =
    recommendation;
  const evidence = evidence_refs ?? [];
  return (
    <div className="border border-gray-200 rounded-lg bg-white p-3 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-gray-900">{title}</p>
        <span className="flex flex-shrink-0 gap-1.5">
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${PRIORITY_STYLES[priority]}`}
            data-testid="priority-badge"
          >
            {capitalizeLevel(priority)}
          </span>
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${RESOLUTION_STYLES[resolution_type]}`}
            data-testid="resolution-badge"
          >
            {resolution_type}
          </span>
        </span>
      </div>

      {(element_type || element_id) && (
        <p className="mt-1 text-xs text-gray-500">
          {element_type}
          {element_id ? ` · ${element_id}` : ''}
        </p>
      )}

      <details className="mt-2">
        <summary className="cursor-pointer select-none text-xs font-semibold uppercase tracking-wide text-gray-500 hover:text-gray-700">
          Details
        </summary>
        <div className="mt-2 space-y-3">
          {reason && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Why it matters</p>
              <p className="mt-1 text-sm leading-relaxed text-gray-700">{reason}</p>
            </div>
          )}
          {suggested_action && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Suggested action</p>
              <p className="mt-1 text-sm leading-relaxed text-gray-800">{suggested_action}</p>
            </div>
          )}
          {evidence.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Evidence</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {evidence.map((ref) => (
                  <span
                    key={ref}
                    className="inline-flex items-center px-2 py-0.5 rounded bg-gray-100 text-xs font-medium text-gray-700"
                    data-testid="evidence-ref"
                  >
                    {ref}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </details>
    </div>
  );
}
