import type { TransformationPlan } from '../types';
import { fetchJson } from './http';

const BASE = '';

export class TransformationService {
  private static instance: TransformationService;

  private constructor() {}

  static getInstance(): TransformationService {
    if (!TransformationService.instance) {
      TransformationService.instance = new TransformationService();
    }
    return TransformationService.instance;
  }

  async interpret(objective: string): Promise<TransformationPlan> {
    const data = await fetchJson<{ plan: TransformationPlan }>(
      `${BASE}/transformations/interpret`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ objective }),
      },
      'Failed to interpret transformation objective',
    );
    return data.plan;
  }
}
