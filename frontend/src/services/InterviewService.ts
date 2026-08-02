import type {
  AdvanceSessionResponse,
  EvidenceReference,
  InterviewReport,
  InterviewSession,
  SubmitAnswerResponse,
} from '../types';

const BASE = '';

function errorDetail(body: unknown, fallback: string): string {
  if (body && typeof body === 'object') {
    const record = body as Record<string, unknown>;
    if (typeof record.detail === 'string') return record.detail;
    if (record.detail && typeof record.detail === 'object') {
      const nested = record.detail as Record<string, unknown>;
      if (typeof nested.detail === 'string') return nested.detail;
    }
  }
  return fallback;
}

export class InterviewService {
  private static instance: InterviewService;

  private constructor() {}

  static getInstance(): InterviewService {
    if (!InterviewService.instance) {
      InterviewService.instance = new InterviewService();
    }
    return InterviewService.instance;
  }

  private async request<T>(url: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${BASE}${url}`, init);
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(errorDetail(body, `Request failed (${response.status})`));
    }
    return response.json();
  }

  async createSession(
    profile: Record<string, unknown>,
    options?: {
      targetRole?: string;
      targetContextId?: string;
      metadata?: Record<string, unknown>;
    },
  ): Promise<InterviewSession> {
    return this.request('/interviews/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile,
        target_role: options?.targetRole,
        target_context_id: options?.targetContextId,
        metadata: options?.metadata,
      }),
    });
  }

  async submitAnswer(
    sessionId: string,
    questionId: string,
    text: string,
    evidenceReferences: EvidenceReference[],
  ): Promise<SubmitAnswerResponse> {
    return this.request(`/interviews/sessions/${encodeURIComponent(sessionId)}/answers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question_id: questionId,
        text,
        evidence_references: evidenceReferences,
      }),
    });
  }

  async nextStep(sessionId: string): Promise<AdvanceSessionResponse> {
    return this.request(`/interviews/sessions/${encodeURIComponent(sessionId)}/next`, {
      method: 'POST',
    });
  }

  async getSession(sessionId: string): Promise<InterviewSession> {
    return this.request(`/interviews/sessions/${encodeURIComponent(sessionId)}`);
  }

  async getReport(sessionId: string): Promise<InterviewReport> {
    return this.request(`/interviews/sessions/${encodeURIComponent(sessionId)}/report`);
  }
}
