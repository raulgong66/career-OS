import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TransformationPage from '../TransformationPage';

const PLAN = {
  plan_id: 'a1b2c3d4e5f67890',
  objective: 'Build a production-grade data platform for real-time analytics on AWS.',
  summary: 'Build a HIPAA-compliant real-time analytics data platform on AWS.',
  phases: [
    {
      phase_id: 'p1_abc123',
      phase_number: 1,
      title: 'Cloud Infrastructure & Security Foundation',
      description: 'Stand up HIPAA-eligible AWS infrastructure with networking, IAM, and audit logging.',
      contract: {
        mission_id: 'm1_abc',
        mission_statement: 'Stand up HIPAA-eligible AWS infrastructure with networking, IAM, and audit logging.',
        summary: 'Stand up HIPAA-eligible AWS infrastructure.',
        role: 'Cloud Security Engineer',
        requirements: ['amazon web services', 'devsecops'],
        concepts: ['cloud-security'],
        capabilities: ['cloud', 'security'],
        evidence_standards: ['production AWS deployment'],
        constraints: ['HIPAA audit logging'],
      },
    },
    {
      phase_id: 'p2_def456',
      phase_number: 2,
      title: 'Data Ingestion Pipeline',
      description: 'Build a real-time data ingestion pipeline handling 100k events per second.',
      contract: {
        mission_id: 'm2_def',
        mission_statement: 'Build a real-time data ingestion pipeline handling 100k events per second.',
        summary: 'Build a real-time data ingestion pipeline.',
        role: 'Data Engineer',
        requirements: ['data pipelines', 'data engineering', 'kubernetes'],
        concepts: ['streaming'],
        capabilities: ['streaming', 'data engineering'],
        evidence_standards: ['production streaming pipeline'],
        constraints: [],
      },
    },
    {
      phase_id: 'p3_ghi789',
      phase_number: 3,
      title: 'Analytics & Machine Learning Layer',
      description: 'Deploy analytics and machine learning models with real-time scoring.',
      contract: {
        mission_id: 'm3_ghi',
        mission_statement: 'Deploy analytics and machine learning models with real-time scoring.',
        summary: 'Deploy analytics and machine learning models.',
        role: 'ML Engineer',
        requirements: ['machine learning', 'python', 'monitoring'],
        concepts: ['machine-learning'],
        capabilities: ['analytics', 'machine learning'],
        evidence_standards: ['production ML platform'],
        constraints: [],
      },
    },
  ],
  constraints: ['HIPAA compliance', 'sub-second latency'],
};

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function renderPage() {
  return render(
    <MemoryRouter>
      <TransformationPage />
    </MemoryRouter>,
  );
}

describe('TransformationPage', () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  let interpretError: boolean;

  beforeEach(() => {
    interpretError = false;
    fetchMock = vi.fn((input: RequestInfo | URL, _init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/transformations/interpret')) {
        if (interpretError) {
          return Promise.resolve(
            jsonResponse({ error: 'INTERPRETATION_FAILED', detail: 'Interpreter failed' }, 422),
          );
        }
        return Promise.resolve(jsonResponse({ plan: PLAN }));
      }
      return Promise.resolve(jsonResponse({}, 404));
    });
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the input phase with objective textarea', () => {
    renderPage();
    expect(screen.getByText('Client Business Objective')).toBeTruthy();
    expect(screen.getByPlaceholderText(/Build a production-grade data platform/i)).toBeTruthy();
    expect(screen.getByRole('button', { name: /Generate Transformation Plan/ })).toBeTruthy();
  });

  it('renders the flow breadcrumb', () => {
    renderPage();
    expect(screen.getByText(/1\. Client objective/)).toBeTruthy();
    expect(screen.getByText(/2\. Proposed transformation/)).toBeTruthy();
  });

  it('calls the interpret endpoint and shows plan phases', async () => {
    renderPage();
    fireEvent.change(screen.getByPlaceholderText(/Build a production-grade data platform/i), {
      target: { value: PLAN.objective },
    });
    fireEvent.click(screen.getByRole('button', { name: /Generate Transformation Plan/ }));
    await waitFor(() => {
      expect(screen.getByText('Cloud Infrastructure & Security Foundation')).toBeTruthy();
    });
    expect(screen.getByText('Data Ingestion Pipeline')).toBeTruthy();
    expect(screen.getByText('Analytics & Machine Learning Layer')).toBeTruthy();
    expect(screen.getByText('3 phases')).toBeTruthy();
  });

  it('shows confirmation button and cross-phase constraints', async () => {
    renderPage();
    fireEvent.change(screen.getByPlaceholderText(/Build a production-grade data platform/i), {
      target: { value: PLAN.objective },
    });
    fireEvent.click(screen.getByRole('button', { name: /Generate Transformation Plan/ }));
    await waitFor(() => {
      expect(screen.getByText('HIPAA compliance')).toBeTruthy();
    });
    expect(screen.getByText('sub-second latency')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Confirm Plan' })).toBeTruthy();
  });

  it('shows error on interpret failure', async () => {
    interpretError = true;
    renderPage();
    fireEvent.change(screen.getByPlaceholderText(/Build a production-grade data platform/i), {
      target: { value: PLAN.objective },
    });
    fireEvent.click(screen.getByRole('button', { name: /Generate Transformation Plan/ }));
    await waitFor(() => {
      expect(screen.getByText(/Interpreter failed/)).toBeTruthy();
    });
  });

  it('phase selection shows phase requirements', async () => {
    renderPage();
    fireEvent.change(screen.getByPlaceholderText(/Build a production-grade data platform/i), {
      target: { value: PLAN.objective },
    });
    fireEvent.click(screen.getByRole('button', { name: /Generate Transformation Plan/ }));
    await screen.findByText('Cloud Infrastructure & Security Foundation');
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Plan' }));
    await screen.findByText('Select a Phase to Evaluate');
    expect(screen.getAllByText(/requirements/).length).toBeGreaterThanOrEqual(3);
  });

  it('plan summary is displayed', async () => {
    renderPage();
    fireEvent.change(screen.getByPlaceholderText(/Build a production-grade data platform/i), {
      target: { value: PLAN.objective },
    });
    fireEvent.click(screen.getByRole('button', { name: /Generate Transformation Plan/ }));
    await waitFor(() => {
      expect(screen.getByText(PLAN.summary)).toBeTruthy();
    });
  });

  it('human review notice is displayed', async () => {
    renderPage();
    fireEvent.change(screen.getByPlaceholderText(/Build a production-grade data platform/i), {
      target: { value: PLAN.objective },
    });
    fireEvent.click(screen.getByRole('button', { name: /Generate Transformation Plan/ }));
    await waitFor(() => {
      expect(screen.getByText(/Human Review Required/)).toBeTruthy();
    });
  });

  it('back button returns to plan view', async () => {
    renderPage();
    fireEvent.change(screen.getByPlaceholderText(/Build a production-grade data platform/i), {
      target: { value: PLAN.objective },
    });
    fireEvent.click(screen.getByRole('button', { name: /Generate Transformation Plan/ }));
    await screen.findByText('Cloud Infrastructure & Security Foundation');
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Plan' }));
    await screen.findByText('Select a Phase to Evaluate');
    fireEvent.click(screen.getByRole('button', { name: 'Back' }));
    await waitFor(() => {
      expect(screen.getByText('Confirm Plan')).toBeTruthy();
    });
  });

  it('selecting a phase highlights it and enables handoff button', async () => {
    renderPage();
    fireEvent.change(screen.getByPlaceholderText(/Build a production-grade data platform/i), {
      target: { value: PLAN.objective },
    });
    fireEvent.click(screen.getByRole('button', { name: /Generate Transformation Plan/ }));
    await screen.findByText('Cloud Infrastructure & Security Foundation');
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Plan' }));
    await screen.findByText('Select a Phase to Evaluate');

    const phase1Button = screen.getByRole('button', { name: /Cloud Infrastructure & Security Foundation/ });
    fireEvent.click(phase1Button);

    await waitFor(() => {
      expect(screen.getByText(/Selected: Phase 1/)).toBeTruthy();
    });
    expect(screen.getByRole('button', { name: /Evaluate Phase 1/ })).toBeTruthy();
  });
});
