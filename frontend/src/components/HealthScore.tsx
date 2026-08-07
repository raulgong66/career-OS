import type { HealthDimensionScore } from '../types';
import DimensionBreakdown from './DimensionBreakdown';
import { healthCategory } from './healthDisplay';

interface HealthScoreProps {
  score: number;
  dimensions: HealthDimensionScore[];
}

function scoreColor(score: number): string {
  if (score >= 80) return 'bg-emerald-500';
  if (score >= 60) return 'bg-blue-500';
  if (score >= 40) return 'bg-amber-500';
  return 'bg-red-500';
}

export default function HealthScore({ score, dimensions }: HealthScoreProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-6">
      <div className="flex flex-col items-center justify-center sm:min-w-36">
        <div
          className={`flex h-28 w-28 flex-col items-center justify-center rounded-full text-white ${scoreColor(score)}`}
          data-testid="health-score"
        >
          <span className="text-4xl font-bold">{score}</span>
          <span className="text-xs font-medium uppercase tracking-wide opacity-90">/ 100</span>
        </div>
        <span
          className="mt-2 inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold text-gray-800"
          data-testid="health-category"
        >
          {healthCategory(score)}
        </span>
      </div>
      <div className="flex-1">
        <DimensionBreakdown dimensions={dimensions} />
      </div>
    </div>
  );
}
