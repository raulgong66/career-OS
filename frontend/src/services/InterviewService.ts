import type { InterviewReport, InterviewSession, NextStepResponse, SubmitAnswerResponse } from '../types';

const BASE = '';

export class InterviewService {
  private static instance: InterviewService;

  private constructor() {}

  static getInstance(): InterviewService {
    if (!InterviewService.instance) {
      InterviewService.instance = new InterviewService();
    }
    return InterviewService.instance;
  }

  async createSession(profileId: string, targetRole?: string): Promise<InterviewSession> {
    const response = await fetch(`${BASE}/interviews/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile_id: profileId, target_role: targetRole }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail ?? 'Failed to start interview');
    }

    return response.json();
  }

  async nextStep(sessionId: string): Promise<NextStepResponse> {
    const response = await fetch(`${BASE}/interviews/sessions/${encodeURIComponent(sessionId)}/next`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail ?? 'Failed to advance interview');
    }

    return response.json();
  }

  async submitAnswer(sessionId: string, text: string, durationSeconds?: number): Promise<SubmitAnswerResponse> {
    const response = await fetch(`${BASE}/interviews/sessions/${encodeURIComponent(sessionId)}/answers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, duration_seconds: durationSeconds }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail ?? 'Failed to submit answer');
    }

    return response.json();
  }

  async pauseSession(sessionId: string): Promise<InterviewSession> {
    const response = await fetch(`${BASE}/interviews/sessions/${encodeURIComponent(sessionId)}/pause`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail ?? 'Failed to pause interview');
    }

    return response.json();
  }

  async resumeSession(sessionId: string): Promise<InterviewSession> {
    const response = await fetch(`${BASE}/interviews/sessions/${encodeURIComponent(sessionId)}/resume`, {
      method: 'POST',
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail ?? 'Failed to resume interview');
    }

    return response.json();
  }

  async getSession(sessionId: string): Promise<InterviewSession> {
    const response = await fetch(`${BASE}/interviews/sessions/${encodeURIComponent(sessionId)}`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail ?? 'Failed to fetch interview');
    }

    return response.json();
  }

  async getReport(sessionId: string): Promise<InterviewReport> {
    const response = await fetch(`${BASE}/interviews/sessions/${encodeURIComponent(sessionId)}/report`);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail ?? 'Failed to fetch interview report');
    }

    return response.json();
  }
}
