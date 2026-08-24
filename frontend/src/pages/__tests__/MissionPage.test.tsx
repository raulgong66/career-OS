import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MissionPage from '../MissionPage';
import type { MissionEvaluationResult } from '../../types';

const CONTRACT = {
  mission_id: 'd32340dae842a70f',
  mission_statement: 'Stand up a security operations capability.',
  summary: 'Stand up a security operations capability.',
  role: 'Security Operations Engineer',
  requirements: ['amazon web services', 'network security'],
  concepts: ['cloud-security'],
  capabilities: ['cloud', 'threat detection'],
  evidence_standards: ['real production experience backed by a source document'],
  constraints: ['managed security services compliance'],
};

const RESULT: MissionEvaluationResult = {
  mission_id: CONTRACT.mission_id,
  mission_statement: CONTRACT.mission_statement,
  role: CONTRACT.role,
  status: 'partial_evidence',
  message: 'Some requirements are evidenced, not all.',
  text_coverage: 75,
  evidence_backed_coverage: 25,
  requirements: [
    {
      requirement: 'amazon web services',
      status: 'evidenced',
      evidence_backed: true,
      referenced: true,
    },
    {
      requirement: 'network security',
      status: 'gap',
      evidence_backed: false,
      referenced: false,
    },
  ],
  recommendations: [],
  candidate: 'Alex Smith',
};

const RESULT_GONGORA: MissionEvaluationResult = {
  ...RESULT,
  status: 'evidence_backed',
  message: 'Every requirement is evidenced with records.',
  text_coverage: 80,
  evidence_backed_coverage: 80,
  requirements: [
    {
      requirement: 'amazon web services',
      status: 'evidenced',
      evidence_backed: true,
      referenced: true,
    },
    {
      requirement: 'network security',
      status: 'referenced_without_evidence',
      evidence_backed: false,
      referenced: true,
    },
  ],
  candidate: 'Raul Gongora',
};

const RESULT_HECHAVARRIA: MissionEvaluationResult = {
  ...RESULT,
  candidate: 'Rene Hechavarria',
};

const PROFILES = [
  { id: 'person-smith', name: 'Alex Smith' },
  { id: 'person-gongora', name: 'Raul Gongora' },
  { id: 'person-hechavarria', name: 'Rene Hechavarria' },
];

function resultFor(profileId: string): MissionEvaluationResult {
  if (profileId === 'person-gongora') return RESULT_GONGORA;
  if (profileId === 'person-hechavarria') return RESULT_HECHAVARRIA;
  return RESULT;
}

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function renderPage() {
  return render(
    <MemoryRouter>
      <MissionPage />
    </MemoryRouter>,
  );
}

async function runMissionToChoose() {
  renderPage();
  fireEvent.change(screen.getByPlaceholderText(/DevSecOps cloud migration team/i), {
    target: { value: CONTRACT.mission_statement },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Start Mission' }));
  await screen.findByRole('heading', { name: 'Confirm the Mission Contract' });
  fireEvent.click(screen.getByRole('button', { name: 'Confirm Mission Contract' }));
  await screen.findByRole('heading', { name: 'Choose Who to Evaluate' });
}

describe('MissionPage', () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  let interpretError: boolean;
  let evaluateError: boolean;

  beforeEach(() => {
    interpretError = false;
    evaluateError = false;
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith('/profiles')) {
        return Promise.resolve(jsonResponse(PROFILES));
      }
      if (url.endsWith('/missions/interpret')) {
        if (interpretError) {
          return Promise.resolve(
            jsonResponse({ error: 'INTERPRETATION_FAILED', detail: 'Interpreter failed' }, 422),
          );
        }
        return Promise.resolve(jsonResponse({ contract: CONTRACT }));
      }
      if (url.endsWith('/missions/evaluate-many')) {
        if (evaluateError) {
          return Promise.resolve(
            jsonResponse({ error: 'INVALID_CONTRACT', detail: 'Contract rejected' }, 422),
          );
        }
        const body = init ? (JSON.parse(String(init.body)) as { profile_ids: string[] }) : { profile_ids: [] };
        return Promise.resolve(
          jsonResponse({
            results: body.profile_ids.map((id) => ({
              profile_id: id,
              result: resultFor(id),
            })),
          }),
        );
      }
      return Promise.resolve(jsonResponse({ detail: `Unexpected fetch: ${url}` }, 500));
    });
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders the mission prompt and start button', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: 'Mission Contract' })).toBeTruthy();
    expect(screen.getByText('What are you trying to accomplish?')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Start Mission' })).toBeTruthy();
  });

  it('does not require a candidate before interpreting and shows the flow', () => {
    renderPage();
    expect(screen.queryByText('Candidate profile')).toBeNull();
    expect(screen.getByText('How it works')).toBeTruthy();
    expect(screen.getByText('Business challenge')).toBeTruthy();
    expect(screen.getByText('Select people for the mission team')).toBeTruthy();
    expect(screen.getByText('Proposed Mission Team')).toBeTruthy();
  });

  it('shows an error when starting with no mission text', () => {
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: 'Start Mission' }));
    expect(screen.getByText('Describe the mission before starting.')).toBeTruthy();
  });

  it('interprets, confirms, selects multiple candidates, and shows each result', async () => {
    await runMissionToChoose();

    expect(screen.getByText('Alex Smith')).toBeTruthy();
    expect(screen.getByText('Raul Gongora')).toBeTruthy();
    expect(screen.getByText('Rene Hechavarria')).toBeTruthy();

    fireEvent.click(screen.getByLabelText('Alex Smith'));
    fireEvent.click(screen.getByLabelText('Raul Gongora'));
    expect(screen.getByText('2 candidates selected')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'Run CareerOS Evaluation' }));

    await screen.findByRole('heading', { name: 'Candidate Results' });
    expect(screen.getByText('Alex Smith')).toBeTruthy();
    expect(screen.getByText('Raul Gongora')).toBeTruthy();
    expect(screen.getByText('Partial evidence')).toBeTruthy();
    expect(screen.getAllByText('Evidence-backed').length).toBeGreaterThan(0);
  });

  it('allows candidates to be deselected', async () => {
    await runMissionToChoose();

    fireEvent.click(screen.getByLabelText('Alex Smith'));
    fireEvent.click(screen.getByLabelText('Raul Gongora'));
    expect(screen.getByText('2 candidates selected')).toBeTruthy();

    fireEvent.click(screen.getByLabelText('Alex Smith'));
    expect(screen.getByText('1 candidate selected')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'Run CareerOS Evaluation' }));
    await screen.findByRole('heading', { name: 'Candidate Results' });
    expect(screen.queryByText('Alex Smith')).toBeNull();
    expect(screen.getByText('Raul Gongora')).toBeTruthy();
  });

  it('keeps evidence limitations visible in results and on the team', async () => {
    await runMissionToChoose();
    fireEvent.click(screen.getByLabelText('Alex Smith'));
    fireEvent.click(screen.getByRole('button', { name: 'Run CareerOS Evaluation' }));
    await screen.findByRole('heading', { name: 'Candidate Results' });

    expect(screen.getByText('Evidence gap')).toBeTruthy();
    expect(screen.getByText('75.0%')).toBeTruthy();
    expect(screen.getByText('25.0%')).toBeTruthy();

    fireEvent.click(screen.getAllByLabelText('Select for Mission Team')[0]);
    fireEvent.click(screen.getByRole('button', { name: 'Review Proposed Mission Team (1)' }));
    await screen.findByRole('heading', { name: 'Proposed Mission Team' });

    expect(screen.getByText('Evidence gap')).toBeTruthy();
    expect(screen.getByText('75.0%')).toBeTruthy();
    expect(screen.getByText('25.0%')).toBeTruthy();
    expect(screen.getByText(/Human review is required/)).toBeTruthy();
  });

  it('shows the team as visibly distinct from merely evaluated candidates', async () => {
    await runMissionToChoose();
    fireEvent.click(screen.getByLabelText('Alex Smith'));
    fireEvent.click(screen.getByLabelText('Raul Gongora'));
    fireEvent.click(screen.getByRole('button', { name: 'Run CareerOS Evaluation' }));
    await screen.findByRole('heading', { name: 'Candidate Results' });

    expect(screen.getByText('Raul Gongora')).toBeTruthy();

    fireEvent.click(screen.getAllByLabelText('Select for Mission Team')[0]);
    fireEvent.click(screen.getByRole('button', { name: 'Review Proposed Mission Team (1)' }));
    await screen.findByRole('heading', { name: 'Proposed Mission Team' });

    expect(screen.getByText(/selected for the mission team/)).toBeTruthy();
    expect(screen.getByText('Alex Smith')).toBeTruthy();
    expect(screen.queryByText('Raul Gongora')).toBeNull();
  });

  it('does not label human-selected candidates as qualified', async () => {
    await runMissionToChoose();
    fireEvent.click(screen.getByLabelText('Alex Smith'));
    fireEvent.click(screen.getByRole('button', { name: 'Run CareerOS Evaluation' }));
    await screen.findByRole('heading', { name: 'Candidate Results' });

    fireEvent.click(screen.getAllByLabelText('Select for Mission Team')[0]);
    fireEvent.click(screen.getByRole('button', { name: 'Review Proposed Mission Team (1)' }));
    await screen.findByRole('heading', { name: 'Proposed Mission Team' });

    expect(screen.getByText('Selected for mission team')).toBeTruthy();
    expect(screen.queryByText(/Qualified/)).toBeNull();
    expect(
      screen.getByText(/Team selection is a human decision\./),
    ).toBeTruthy();
  });

  it('surfaces an interpretation error', async () => {
    interpretError = true;
    renderPage();
    fireEvent.change(screen.getByPlaceholderText(/DevSecOps cloud migration team/i), {
      target: { value: CONTRACT.mission_statement },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Start Mission' }));
    await waitFor(() => {
      expect(screen.getByText(/Interpreter failed/)).toBeTruthy();
    });
  });

  it('surfaces an evaluation error', async () => {
    evaluateError = true;
    await runMissionToChoose();
    fireEvent.click(screen.getByLabelText('Alex Smith'));
    fireEvent.click(screen.getByRole('button', { name: 'Run CareerOS Evaluation' }));
    await waitFor(() => {
      expect(screen.getByText(/Contract rejected/)).toBeTruthy();
    });
  });
});
