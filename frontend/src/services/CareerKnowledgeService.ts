import type { KnowledgeAnswer } from '../types';

const BASE = '';

export class CareerKnowledgeService {
  private static instance: CareerKnowledgeService;

  private constructor() {}

  static getInstance(): CareerKnowledgeService {
    if (!CareerKnowledgeService.instance) {
      CareerKnowledgeService.instance = new CareerKnowledgeService();
    }
    return CareerKnowledgeService.instance;
  }

  async ask(question: string): Promise<KnowledgeAnswer> {
    const params = new URLSearchParams({ q: question });
    const response = await fetch(`${BASE}/csks/query?${params.toString()}`);

    if (!response.ok) {
      let message = 'Failed to query Career Knowledge';
      try {
        const error = await response.json();
        if (error && typeof error.detail === 'string') {
          message = error.detail;
        }
      } catch {
        // Non-JSON error body; keep the default message.
      }
      throw new Error(message);
    }

    return response.json();
  }
}
