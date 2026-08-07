import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ArtifactWorkspacePage from '../ArtifactWorkspacePage';

const TEMPLATES = [
  { id: 'standard_cv', displayName: 'Tailored CV', artifactType: 'CV' },
  { id: 'standard_interest_letter', displayName: 'Interest Letter', artifactType: 'INTEREST_LETTER' },
];

const PROFILES = [
  {
    id: 'profile-1',
    name: 'Jane Doe',
    headline: 'AI Engineer',
    artifactCount: 0,
    artifactIds: [],
    importedAt: '2026-01-01',
  },
];

const BASE_DETAILS = {
  id: 'profile-1',
  person: {
    firstName: 'Jane',
    lastName: 'Doe',
    headline: 'AI Engineer',
    city: null,
    country: null,
    languages: [],
  },
  summary: 'Summary text',
  importedAt: '2026-01-01',
  professionalSummaries: [],
  experiences: [],
  skills: [],
  education: [],
  certifications: [],
  projects: [],
};

const PROFILE_DETAILS = { ...BASE_DETAILS, artifacts: [] };

const PROFILE_WITH_ARTIFACT = {
  ...BASE_DETAILS,
  artifacts: [
    { id: 'artifact-1', type: 'CV', name: 'Tailored CV', sourceCount: 3, status: 'current' },
  ],
};

const PREVIEW = {
  markdown: '# Preview Resume\n\n## Core Competencies\n\n- Python',
  source_count: 3,
  estimated_health_score: 78,
};

const INTEREST_PREVIEW = {
  markdown: '# Preview\n\nDear Hiring Team,\n\nInterest letter content.',
  source_count: 2,
  estimated_health_score: 78,
};

const QUALITY_REPORT = {
  health_score: 78,
  dimensions: [
    { name: 'achievements', score: 90, weight: 0.4 },
    { name: 'skills', score: 66, weight: 0.3 },
  ],
  findings: [
    {
      rule_id: 'quality:achievement-measurability',
      dimension: 'achievements',
      element_id: 'exp-1',
      element_type: 'experience',
      title: 'Strengthen quantified impact in work experience',
      reason: '3 experiences lack metrics.',
      suggested_action: 'Add numbers to outcomes.',
      resolution_type: 'guided',
      evidence_refs: [],
      priority: 'high',
      estimated_impact: 'high',
      confidence: 'medium',
      citations: [],
    },
  ],
  citations: [],
};

const QUEUE = [
  {
    id: 'rec-1',
    source: 'profile_quality',
    rule_id: 'quality:achievement-measurability',
    element_id: 'exp-1',
    element_type: 'experience',
    title: 'Strengthen quantified impact in work experience',
    reason: '3 experiences lack metrics.',
    suggested_action: 'Add numbers to outcomes.',
    resolution_type: 'guided',
    evidence_refs: ['exp-1.details'],
    priority: 'high',
    estimated_impact: 'high',
    confidence: 'medium',
    jd_match_score: null,
    context_match_score: null,
    weighted_total: null,
  },
  {
    id: 'rec-2',
    source: 'profile_quality',
    rule_id: 'recommendation_add_measurable_achievement',
    element_id: 'exp-1',
    element_type: 'experience',
    title: 'Add measurable achievements',
    reason: 'This experience has no quantified outcomes.',
    suggested_action: 'Add a measurable achievement statement.',
    resolution_type: 'auto',
    evidence_refs: ['exp-1.details'],
    priority: 'high',
    estimated_impact: 'high',
    confidence: 'medium',
    jd_match_score: null,
    context_match_score: null,
    weighted_total: null,
  },
];

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function textResponse(text: string, status = 200): Response {
  return new Response(text, { status, headers: { 'Content-Type': 'text/markdown' } });
}

function methodOf(init?: RequestInit): string {
  return init?.method ?? 'GET';
}

function renderPage() {
  return render(
    <MemoryRouter>
      <ArtifactWorkspacePage />
    </MemoryRouter>,
  );
}

describe('ArtifactWorkspacePage', () => {
  let artifactsCreated: boolean;
  let fetchMock: ReturnType<typeof vi.fn>;
  let previewPending: boolean;

  beforeEach(() => {
    artifactsCreated = false;
    previewPending = false;
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (method === 'GET' && url.endsWith('/artifact-templates')) {
        return Promise.resolve(jsonResponse(TEMPLATES));
      }
      if (method === 'GET' && url.endsWith('/profiles')) {
        return Promise.resolve(jsonResponse(PROFILES));
      }
      if (method === 'GET' && /\/profiles\/profile-1$/.test(url)) {
        return Promise.resolve(jsonResponse(artifactsCreated ? PROFILE_WITH_ARTIFACT : PROFILE_DETAILS));
      }
      if (method === 'GET' && url.endsWith('/profiles/profile-1/quality-report')) {
        return Promise.resolve(jsonResponse(QUALITY_REPORT));
      }
      if (method === 'GET' && url.includes('/profiles/profile-1/improvement-queue')) {
        return Promise.resolve(jsonResponse(QUEUE));
      }
      if (method === 'GET' && url.endsWith('/technologies')) {
        return Promise.resolve(jsonResponse({ keywords: ['python', 'docker', 'kubernetes'] }));
      }
      if (method === 'POST' && url.endsWith('/artifact-templates/standard_cv/preview')) {
        return previewPending
          ? new Promise<Response>(() => {})
          : Promise.resolve(jsonResponse(PREVIEW));
      }
      if (method === 'POST' && url.endsWith('/artifact-templates/standard_interest_letter/preview')) {
        return Promise.resolve(jsonResponse(INTEREST_PREVIEW));
      }
      if (method === 'POST' && url.endsWith('/profiles/profile-1/artifacts')) {
        artifactsCreated = true;
        return Promise.resolve(jsonResponse({ artifactId: 'artifact-1' }));
      }
      if (method === 'POST' && url.endsWith('/generate/artifact')) {
        return Promise.resolve(textResponse('# Generated CV\n\nContent here.'));
      }
      return Promise.resolve(jsonResponse({ detail: `Unexpected fetch: ${method} ${url}` }, 500));
    });
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('auto-preview renders the default CV template on load', async () => {
    renderPage();

    expect(await screen.findByRole('heading', { name: 'Preview Resume' })).toBeTruthy();
    expect(screen.getByText('Python')).toBeTruthy();
    expect(screen.getByTestId('preview-source-count').textContent).toContain('3 sources rendered');
    expect(screen.getByText('Generate Resume')).toBeTruthy();
  });

  it('selecting a template previews it through the preview endpoint', async () => {
    renderPage();
    await screen.findByRole('heading', { name: 'Preview Resume' });

    fireEvent.click(screen.getByText('Interest Letter'));

    await screen.findByRole('heading', { name: 'Preview' });
    expect(screen.getByText('Interest letter content.')).toBeTruthy();

    const previewCalls = fetchMock.mock.calls.filter((call) =>
      String(call[0]).endsWith('/artifact-templates/standard_interest_letter/preview'),
    );
    expect(previewCalls.length).toBe(1);
  });

  it('refresh preview re-requests the template preview endpoint', async () => {
    renderPage();
    await screen.findByRole('heading', { name: 'Preview Resume' });

    fireEvent.click(screen.getByText('Refresh Preview'));

    await waitFor(() => {
      const previewCalls = fetchMock.mock.calls.filter((call) =>
        String(call[0]).endsWith('/artifact-templates/standard_cv/preview'),
      );
      expect(previewCalls.length).toBe(2);
    });
  });

  it('generate resume creates the artifact and shows the generated artifact preview', async () => {
    renderPage();
    await screen.findByRole('heading', { name: 'Preview Resume' });

    fireEvent.click(screen.getByText('Generate Resume'));

    expect(await screen.findByRole('heading', { name: 'Generated CV' })).toBeTruthy();
    expect(screen.getByText('Content here.')).toBeTruthy();

    const createCalls = fetchMock.mock.calls.filter((call) =>
      String(call[0]).endsWith('/profiles/profile-1/artifacts'),
    );
    expect(createCalls.length).toBe(1);

    await waitFor(() => {
      expect(screen.getByText('current')).toBeTruthy();
    });
    expect(screen.getByText('artifact-1')).toBeTruthy();
  });

  it('generate resume is disabled when an artifact already exists for the template', async () => {
    artifactsCreated = true;
    renderPage();

    const generateButton = await screen.findByRole('button', { name: 'Generate Resume' });
    expect((generateButton as HTMLButtonElement).disabled).toBe(true);
  });

  it('shows loading state while preview renders', async () => {
    previewPending = true;
    renderPage();

    expect(await screen.findByText('Rendering preview...')).toBeTruthy();
  });

  it('shows the active profile context and profile health on load', async () => {
    renderPage();

    expect(screen.getByText('ACTIVE PROFILE')).toBeTruthy();
    expect((await screen.findByTestId('active-profile-name')).textContent).toBe('Jane Doe');
    expect(screen.getByTestId('active-profile-headline').textContent).toBe('AI Engineer');

    const score = await screen.findByTestId('health-score');
    expect(score.textContent).toContain('78');
    expect(screen.getByTestId('health-category').textContent).toContain('Solid');

    expect(screen.getByText('Improvement Queue')).toBeTruthy();
    expect(screen.getAllByText('Strengthen quantified impact in work experience').length).toBeGreaterThan(0);
    expect(screen.getByText('1 improvement suggested across 2 health dimensions.')).toBeTruthy();
  });

  it('refresh re-requests the quality report and improvement queue', async () => {
    renderPage();
    await screen.findByTestId('health-score');

    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));

    await waitFor(() => {
      const reportCalls = fetchMock.mock.calls.filter((call) =>
        String(call[0]).endsWith('/profiles/profile-1/quality-report'),
      );
      expect(reportCalls.length).toBe(2);
    });
  });

  it('filtering the improvement queue reloads recommendations with the filter', async () => {
    renderPage();
    await screen.findByTestId('health-score');

    fireEvent.change(screen.getByLabelText('Priority'), { target: { value: 'high' } });

    await waitFor(() => {
      const queueCalls = fetchMock.mock.calls.filter((call) =>
        String(call[0]).includes('/profiles/profile-1/improvement-queue'),
      );
      expect(queueCalls.some((call) => String(call[0]).includes('priority=high'))).toBe(true);
    });
  });

  it('shows error state when preview fails', async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      if (method === 'GET' && url.endsWith('/artifact-templates')) {
        return Promise.resolve(jsonResponse(TEMPLATES));
      }
      if (method === 'GET' && url.endsWith('/profiles')) {
        return Promise.resolve(jsonResponse(PROFILES));
      }
      if (method === 'GET' && /\/profiles\/profile-1$/.test(url)) {
        return Promise.resolve(jsonResponse(PROFILE_DETAILS));
      }
      if (method === 'POST' && url.endsWith('/preview')) {
        return Promise.resolve(jsonResponse({ detail: 'Preview exploded' }, 500));
      }
      return Promise.resolve(jsonResponse({ detail: `Unexpected fetch: ${method} ${url}` }, 500));
    });

    renderPage();

    expect(await screen.findByText('Preview exploded (HTTP 500)')).toBeTruthy();
    expect(screen.getByText('Try again')).toBeTruthy();
  });

  it('shows a friendly error (with status) when the backend returns a plain-text 500', async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      if (method === 'GET' && url.endsWith('/artifact-templates')) {
        return Promise.resolve(jsonResponse(TEMPLATES));
      }
      if (method === 'GET' && url.endsWith('/profiles')) {
        return Promise.resolve(jsonResponse(PROFILES));
      }
      if (method === 'GET' && /\/profiles\/profile-1$/.test(url)) {
        return Promise.resolve(jsonResponse(PROFILE_DETAILS));
      }
      if (method === 'GET' && url.endsWith('/profiles/profile-1/quality-report')) {
        return Promise.resolve(textResponse('Internal Server Error', 500));
      }
      if (method === 'GET' && url.includes('/profiles/profile-1/improvement-queue')) {
        return Promise.resolve(jsonResponse([]));
      }
      if (method === 'POST' && url.endsWith('/artifact-templates/standard_cv/preview')) {
        return Promise.resolve(jsonResponse(PREVIEW));
      }
      return Promise.resolve(jsonResponse({ detail: `Unexpected fetch: ${method} ${url}` }, 500));
    });

    renderPage();

    expect(await screen.findByTestId('health-error')).toBeTruthy();
    expect(screen.getByTestId('health-error').textContent).toContain('Internal Server Error');
    expect(screen.getByTestId('health-error').textContent).toContain('(HTTP 500)');
  });

  it('shows a graceful error when the backend returns non-JSON content on a success status', async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';
      if (method === 'GET' && url.endsWith('/artifact-templates')) {
        return Promise.resolve(jsonResponse(TEMPLATES));
      }
      if (method === 'GET' && url.endsWith('/profiles')) {
        return Promise.resolve(jsonResponse(PROFILES));
      }
      if (method === 'GET' && /\/profiles\/profile-1$/.test(url)) {
        return Promise.resolve(jsonResponse(PROFILE_DETAILS));
      }
      if (method === 'POST' && url.endsWith('/artifact-templates/standard_cv/preview')) {
        return Promise.resolve(textResponse('This is not JSON at all', 200));
      }
      return Promise.resolve(jsonResponse({ detail: `Unexpected fetch: ${method} ${url}` }, 500));
    });

    renderPage();

    expect(await screen.findByText('Invalid response from server (expected JSON).')).toBeTruthy();
    expect(screen.getByText('Try again')).toBeTruthy();
  });

  it('resolvable recommendation shows a Resolve button that opens the panel', async () => {
    renderPage();
    await screen.findByTestId('health-score');

    const resolveButtons = screen.getAllByTestId('resolve-button');
    expect(resolveButtons.length).toBe(1);

    fireEvent.click(resolveButtons[0]);

    expect(await screen.findByTestId('resolution-panel')).toBeTruthy();
    expect(screen.getByText('Resolve recommendation')).toBeTruthy();
  });

  it('apply resolution calls resolve endpoint and triggers auto-refresh chain', async () => {

    let resolveFinished: (value: Response | PromiseLike<Response>) => void;
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? 'GET';

      if (method === 'GET' && url.endsWith('/artifact-templates')) {
        return Promise.resolve(jsonResponse(TEMPLATES));
      }
      if (method === 'GET' && url.endsWith('/profiles')) {
        return Promise.resolve(jsonResponse(PROFILES));
      }
      if (method === 'GET' && /\/profiles\/profile-1$/.test(url)) {
        return Promise.resolve(jsonResponse(PROFILE_DETAILS));
      }
      if (method === 'GET' && url.endsWith('/profiles/profile-1/quality-report')) {
        return Promise.resolve(jsonResponse(QUALITY_REPORT));
      }
      if (method === 'GET' && url.includes('/profiles/profile-1/improvement-queue')) {
        return Promise.resolve(jsonResponse(QUEUE));
      }
      if (method === 'GET' && url.endsWith('/technologies')) {
        return Promise.resolve(jsonResponse({ keywords: [] }));
      }
      if (method === 'POST' && url.endsWith('/artifact-templates/standard_cv/preview')) {
        return Promise.resolve(jsonResponse(PREVIEW));
      }
      if (method === 'POST' && url.endsWith('/profiles/profile-1/resolve')) {
        return new Promise<Response>((resolve) => { resolveFinished = resolve; });
      }
      return Promise.resolve(jsonResponse({ detail: `Unexpected fetch: ${method} ${url}` }, 500));
    });

    renderPage();
    await screen.findByTestId('health-score');

    const resolveButtons = screen.getAllByTestId('resolve-button');
    fireEvent.click(resolveButtons[0]);
    await screen.findByTestId('resolution-panel');

    fireEvent.change(screen.getByPlaceholderText('e.g. Reduced deployment time by 60%'), { target: { value: 'Reduced incidents by 40%' } });
    fireEvent.click(screen.getByTestId('resolution-apply'));

    expect(await screen.findByText('Applying resolution...')).toBeTruthy();
    const resolveCalls = fetchMock.mock.calls.filter((call) =>
      String(call[0]).endsWith('/profiles/profile-1/resolve'),
    );
    expect(resolveCalls.length).toBe(1);
    expect(resolveCalls[0][1]?.body).toContain('NoMeasurableAchievementRule');
    expect(resolveCalls[0][1]?.body).toContain('Reduced incidents by 40%');

    resolveFinished!(jsonResponse({ profile: PROFILE_DETAILS }));
    await waitFor(() => {
      expect(screen.getByText('Done')).toBeTruthy();
    });
    expect(screen.queryByTestId('resolution-panel')).toBeNull();

    const profileCalls = fetchMock.mock.calls.filter((call) =>
      methodOf(call[1]) === 'GET' && /\/profiles\/profile-1$/.test(String(call[0])),
    );
    expect(profileCalls.length).toBeGreaterThanOrEqual(2);
    const reportCalls = fetchMock.mock.calls.filter((call) =>
      String(call[0]).endsWith('/profiles/profile-1/quality-report'),
    );
    expect(reportCalls.length).toBeGreaterThanOrEqual(2);
    const queueCallsAfterResolve = fetchMock.mock.calls
      .filter((call) => String(call[0]).includes('/profiles/profile-1/improvement-queue'))
      .map((call) => String(call[0]));
    expect(queueCallsAfterResolve.length).toBeGreaterThanOrEqual(2);
    const previewCallsAfterResolve = fetchMock.mock.calls
      .filter((call) => String(call[0]).endsWith('/artifact-templates/standard_cv/preview'))
      .map((call) => String(call[0]));
    expect(previewCallsAfterResolve.length).toBeGreaterThanOrEqual(2);
  });

  describe('profile switching', () => {
    const PROFILES_TWO = [
      { id: 'profile-1', name: 'Jane Doe', headline: 'AI Engineer', artifactCount: 0, artifactIds: [], importedAt: '2026-01-01' },
      { id: 'profile-2', name: 'Bob Smith', headline: 'Backend Engineer', artifactCount: 0, artifactIds: [], importedAt: '2026-01-02' },
    ];

    const DETAILS_2 = {
      id: 'profile-2',
      person: {
        firstName: 'Bob',
        lastName: 'Smith',
        headline: 'Backend Engineer',
        city: null,
        country: null,
        languages: [],
      },
      summary: 'Bob summary',
      importedAt: '2026-01-02',
      professionalSummaries: [],
      experiences: [],
      skills: [],
      education: [],
      certifications: [],
      projects: [],
      artifacts: [
        { id: 'artifact-2', type: 'CV', name: 'Bob Tailored CV', sourceCount: 5, status: 'current' },
      ],
    };

    const PREVIEW_2 = {
      markdown: '# Bob Preview\n\n## Core Competencies\n\n- Go',
      source_count: 5,
      estimated_health_score: 60,
    };

    const QUALITY_REPORT_2 = {
      health_score: 55,
      dimensions: [{ name: 'achievements', score: 55, weight: 1.0 }],
      findings: [],
      citations: [],
    };

    function deferredResponse(): { promise: Promise<Response>; resolve: (r: Response) => void } {
      let resolveFn!: (r: Response) => void;
      const promise = new Promise<Response>((resolve) => { resolveFn = resolve; });
      return { promise, resolve: resolveFn };
    }

    function immediateFetchMock(opts: {
      profile2Gate?: ReturnType<typeof deferredResponse>;
      firstPreviewGate?: ReturnType<typeof deferredResponse>;
      profile2QualityError?: string;
    }) {
      let firstPreviewCall = true;
      return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = init?.method ?? 'GET';

        if (method === 'GET' && url.endsWith('/artifact-templates')) {
          return Promise.resolve(jsonResponse(TEMPLATES));
        }
        if (method === 'GET' && url.endsWith('/profiles')) {
          return Promise.resolve(jsonResponse(PROFILES_TWO));
        }
        if (method === 'GET' && /\/profiles\/profile-1$/.test(url)) {
          return Promise.resolve(jsonResponse(PROFILE_DETAILS));
        }
        if (method === 'GET' && /\/profiles\/profile-2$/.test(url)) {
          return opts.profile2Gate
            ? opts.profile2Gate.promise
            : Promise.resolve(jsonResponse(DETAILS_2));
        }
        if (method === 'GET' && url.endsWith('/profiles/profile-1/quality-report')) {
          return Promise.resolve(jsonResponse(QUALITY_REPORT));
        }
        if (method === 'GET' && url.includes('/profiles/profile-1/improvement-queue')) {
          return Promise.resolve(jsonResponse(QUEUE));
        }
        if (method === 'GET' && url.endsWith('/profiles/profile-2/quality-report')) {
          if (opts.profile2QualityError) {
            return Promise.resolve(jsonResponse({ detail: opts.profile2QualityError }, 500));
          }
          return Promise.resolve(jsonResponse(QUALITY_REPORT_2));
        }
        if (method === 'GET' && url.includes('/profiles/profile-2/improvement-queue')) {
          return Promise.resolve(jsonResponse([]));
        }
        if (method === 'POST' && url.endsWith('/artifact-templates/standard_cv/preview')) {
          let bodyProfileId = '';
          try {
            bodyProfileId =
              (JSON.parse(String(init?.body ?? '{}')) as { profile_id?: string }).profile_id ?? '';
          } catch {
            bodyProfileId = '';
          }
          if (opts.firstPreviewGate && firstPreviewCall) {
            firstPreviewCall = false;
            return opts.firstPreviewGate.promise;
          }
          firstPreviewCall = false;
          return Promise.resolve(jsonResponse(bodyProfileId === 'profile-2' ? PREVIEW_2 : PREVIEW));
        }
        if (method === 'POST' && url.endsWith('/artifact-templates/standard_interest_letter/preview')) {
          return Promise.resolve(jsonResponse(INTEREST_PREVIEW));
        }
        return Promise.resolve(jsonResponse({ detail: `Unexpected fetch: ${method} ${url}` }, 500));
      });
    }

    it('ignores a stale profile details response for a previously active profile', async () => {
      const profile2Gate = deferredResponse();
      vi.stubGlobal('fetch', immediateFetchMock({ profile2Gate }));

      renderPage();
      await screen.findByTestId('active-profile-name');

      fireEvent.change(screen.getByLabelText('Switch Profile'), { target: { value: 'profile-2' } });

      fireEvent.change(screen.getByLabelText('Switch Profile'), { target: { value: 'profile-1' } });

      await waitFor(() => {
        expect(screen.getByTestId('active-profile-name').textContent).toBe('Jane Doe');
      });

      profile2Gate.resolve(jsonResponse(DETAILS_2));
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(screen.getByTestId('active-profile-name').textContent).toBe('Jane Doe');
      expect(screen.getByTestId('active-profile-headline').textContent).toBe('AI Engineer');
      expect(screen.queryByText('Bob Tailored CV')).toBeNull();
    });

    it('ignores a stale template preview response after switching profiles', async () => {
      const firstPreviewGate = deferredResponse();
      const fetchMock = immediateFetchMock({ firstPreviewGate });
      vi.stubGlobal('fetch', fetchMock);

      renderPage();
      await screen.findByTestId('active-profile-name');

      const previewCalls = () =>
        fetchMock.mock.calls.filter((call) =>
          String(call[0]).endsWith('/artifact-templates/standard_cv/preview'),
        );

      expect(previewCalls().length).toBe(1);

      fireEvent.change(screen.getByLabelText('Switch Profile'), { target: { value: 'profile-2' } });

      await screen.findByText('Go');
      expect(screen.getByText('Bob Preview')).toBeTruthy();

      firstPreviewGate.resolve(jsonResponse(PREVIEW));
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(screen.getByText('Go')).toBeTruthy();
      expect(screen.queryByText('Python')).toBeNull();
    });

    it('updates profile health after switching to another imported profile', async () => {
      vi.stubGlobal('fetch', immediateFetchMock({}));

      renderPage();
      await screen.findByTestId('health-score');
      expect(screen.getByTestId('health-score').textContent).toContain('78');

      fireEvent.change(screen.getByLabelText('Switch Profile'), { target: { value: 'profile-2' } });

      await waitFor(() => {
        expect(screen.getByTestId('active-profile-name').textContent).toBe('Bob Smith');
      });
      await waitFor(() => {
        expect(screen.getByTestId('health-score').textContent).toContain('55');
      });
    });

    it('keeps profile health in sync when switching back and forth between profiles', async () => {
      vi.stubGlobal('fetch', immediateFetchMock({}));

      renderPage();
      await screen.findByTestId('active-profile-name');

      fireEvent.change(screen.getByLabelText('Switch Profile'), { target: { value: 'profile-2' } });
      await waitFor(() => {
        expect(screen.getByTestId('active-profile-name').textContent).toBe('Bob Smith');
      });
      await waitFor(() => {
        expect(screen.getByTestId('health-score').textContent).toContain('55');
      });

      fireEvent.change(screen.getByLabelText('Switch Profile'), { target: { value: 'profile-1' } });
      await waitFor(() => {
        expect(screen.getByTestId('active-profile-name').textContent).toBe('Jane Doe');
      });
      await waitFor(() => {
        expect(screen.getByTestId('health-score').textContent).toContain('78');
      });
    });

    it('shows a health error for the newly selected profile when its quality report fails', async () => {
      vi.stubGlobal('fetch', immediateFetchMock({ profile2QualityError: 'Quality analysis failed' }));

      renderPage();
      await screen.findByTestId('health-score');

      fireEvent.change(screen.getByLabelText('Switch Profile'), { target: { value: 'profile-2' } });

      await waitFor(() => {
        expect(screen.getByTestId('active-profile-name').textContent).toBe('Bob Smith');
      });
      expect(await screen.findByTestId('health-error')).toBeTruthy();
      expect(screen.getByTestId('health-error').textContent).toContain('Quality analysis failed (HTTP 500)');
    });
  });
});
