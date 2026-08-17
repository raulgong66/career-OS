import type {
  MissionCandidateEvaluation,
  MissionContract,
  MissionEvaluationResult,
} from '../types';
import { fetchJson } from './http';

const BASE = '';

export class MissionService {
  private static instance: MissionService;

  private constructor() {}

  static getInstance(): MissionService {
    if (!MissionService.instance) {
      MissionService.instance = new MissionService();
    }
    return MissionService.instance;
  }

  async interpret(mission: string): Promise<MissionContract> {
    const data = await fetchJson<{ contract: MissionContract }>(
      `${BASE}/missions/interpret`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mission }),
      },
      'Failed to interpret mission',
    );
    return data.contract;
  }

  async evaluate(
    profileId: string,
    contract: MissionContract,
  ): Promise<MissionEvaluationResult> {
    const data = await fetchJson<{ result: MissionEvaluationResult }>(
      `${BASE}/missions/evaluate`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id: profileId, contract }),
      },
      'Failed to evaluate mission',
    );
    return data.result;
  }

  async evaluateMany(
    profileIds: string[],
    contract: MissionContract,
  ): Promise<MissionCandidateEvaluation[]> {
    const data = await fetchJson<{ results: MissionCandidateEvaluation[] }>(
      `${BASE}/missions/evaluate-many`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_ids: profileIds, contract }),
      },
      'Failed to evaluate candidates',
    );
    return data.results;
  }
}
