import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CareerKnowledgePage from '../CareerKnowledgePage';

const ANSWER = {
  answer: 'CareerOS is the platform domain.',
  citations: [
    {
      file: 'docs/architecture/02-domain-map.md',
      line_start: 47,
      line_end: 47,
      text: 'CareerOS - domain',
      entity_id: 'domain.careeros',
    },
    {
      file: 'docs/architecture/01-system-overview.md',
      line_start: 3,
      line_end: 3,
      text: 'System overview',
      entity_id: 'document.01-system-overview',
    },
  ],
  confidence: 0.95,
  entities_found: 2,
  query_time_ms: 4,
  query_type: 'entity_lookup',
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
      <CareerKnowledgePage />
    </MemoryRouter>,
  );
}

describe('CareerKnowledgePage', () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  let queryPending: boolean;
  let queryError: boolean;

  beforeEach(() => {
    queryPending = false;
    queryError = false;
    fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/csks/query')) {
        if (queryPending) {
          return new Promise<Response>(() => {});
        }
        if (queryError) {
          return Promise.resolve(jsonResponse({ detail: 'Backend unavailable' }, 500));
        }
        return Promise.resolve(jsonResponse(ANSWER));
      }
      return Promise.resolve(jsonResponse({ detail: `Unexpected fetch: ${url}` }, 500));
    });
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders the page heading and subtitle', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: 'Career Knowledge' })).toBeTruthy();
    expect(
      screen.getByText('Powered by the Career Self Knowledge System')
    ).toBeTruthy();
    expect(screen.getByText('Ask CareerOS about itself.')).toBeTruthy();
  });

  it('renders the search box and Ask button', () => {
    renderPage();
    expect(screen.getByPlaceholderText('e.g. What is CareerOS?')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Ask' })).toBeTruthy();
  });

  it('renders the example questions under "Try asking"', () => {
    renderPage();
    expect(screen.getByText('Try asking')).toBeTruthy();
    expect(screen.getByText('What is CareerOS?')).toBeTruthy();
    expect(screen.getByText('How is AI applied?')).toBeTruthy();
    expect(screen.getByText('How does artifact generation work?')).toBeTruthy();
    expect(screen.getByText('Explain the Resolution Engine')).toBeTruthy();
  });

  it('renders the Knowledge Explorer topics as chips', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: 'Knowledge Explorer' })).toBeTruthy();
    for (const topic of [
      'CareerOS',
      'Artifact Generation',
      'AI',
      'Reasoning',
      'Resolution',
      'Interview',
      'Profile Management',
    ]) {
      expect(screen.getByRole('button', { name: topic })).toBeTruthy();
    }
  });

  it('renders empty placeholder sections for Answer, Sources and Confidence', () => {
    renderPage();
    expect(screen.getByText('Answer')).toBeTruthy();
    expect(screen.getByText('Sources')).toBeTruthy();
    expect(screen.getByText('Confidence')).toBeTruthy();
  });

  it('shows a "← Back to Home" button', () => {
    renderPage();
    expect(screen.getByRole('button', { name: '← Back to Home' })).toBeTruthy();
  });

  it('pre-fills the search box when an example question is clicked', () => {
    renderPage();
    const input = screen.getByPlaceholderText('e.g. What is CareerOS?');
    fireEvent.click(screen.getByText('How does artifact generation work?'));
    expect((input as HTMLInputElement).value).toBe('How does artifact generation work?');
  });

  it('populates the search box when an explorer chip is clicked without executing', () => {
    renderPage();
    const input = screen.getByPlaceholderText('e.g. What is CareerOS?');
    fireEvent.click(screen.getByRole('button', { name: 'Artifact Generation' }));
    expect((input as HTMLInputElement).value).toBe('Artifact Generation');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('executes the query and renders answer, sources and confidence', async () => {
    renderPage();
    fireEvent.change(screen.getByPlaceholderText('e.g. What is CareerOS?'), {
      target: { value: 'What is CareerOS?' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));

    const url = String(fetchMock.mock.calls[0][0]);
    expect(url.startsWith('/csks/query?q=')).toBe(true);
    expect(url).toContain('CareerOS');

    expect(await screen.findByText('CareerOS is the platform domain.')).toBeTruthy();
    expect(screen.getByText('docs/architecture/02-domain-map.md:47')).toBeTruthy();
    expect(screen.getByText('docs/architecture/01-system-overview.md:3')).toBeTruthy();
    expect(screen.getByText('95%')).toBeTruthy();
  });

  it('disables Ask and shows loading text while the query is pending', () => {
    queryPending = true;
    renderPage();
    fireEvent.change(screen.getByPlaceholderText('e.g. What is CareerOS?'), {
      target: { value: 'What is CareerOS?' },
    });
    const askButton = screen.getByRole('button', { name: 'Ask' });
    fireEvent.click(askButton);

    expect(screen.getByText('Asking CareerOS...')).toBeTruthy();
    expect((askButton as HTMLButtonElement).disabled).toBe(true);
  });

  it('renders a friendly error when the backend fails', async () => {
    queryError = true;
    renderPage();
    fireEvent.change(screen.getByPlaceholderText('e.g. What is CareerOS?'), {
      target: { value: 'What is CareerOS?' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));

    expect(await screen.findByRole('alert')).toBeTruthy();
    expect(screen.getByText('Backend unavailable')).toBeTruthy();
  });
});
