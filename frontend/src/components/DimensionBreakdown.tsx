import type { HealthDimensionScore } from '../types';
import { dimensionLabel } from './healthDisplay';

interface DimensionBreakdownProps {
  dimensions: HealthDimensionScore[];
}

export default function DimensionBreakdown({ dimensions }: DimensionBreakdownProps) {
  return (
    <div className="space-y-2.5">
      {dimensions.map((dimension) => (
        <div key={dimension.name}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-gray-700">
              {dimensionLabel(dimension.name)}
            </span>
            <span className="text-xs font-semibold text-gray-900">
              {Math.round(dimension.score * 100)}
            </span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-gray-100">
            <div
              className="h-1.5 rounded-full bg-blue-500"
              style={{ width: `${Math.max(0, Math.min(100, Math.round(dimension.score * 100)))}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
