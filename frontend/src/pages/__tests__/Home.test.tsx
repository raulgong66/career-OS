import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Home from '../Home';

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('Home', () => {
  beforeEach(() => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/profiles')) {
        return Promise.resolve(jsonResponse([]));
      }
      return Promise.resolve(jsonResponse({ detail: `Unexpected fetch: ${url}` }, 500));
    });
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders the Mission Contract card as a coming-next entry point', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>,
    );
    expect(screen.getByText('Mission Contract')).toBeTruthy();
    expect(
      screen.getByText('Turn a business challenge into an evidence-ready workforce mission.'),
    ).toBeTruthy();
    expect(screen.getAllByText('COMING NEXT').length).toBeGreaterThan(0);
    expect(screen.getAllByRole('button', { name: 'Open →' }).length).toBeGreaterThanOrEqual(1);
  });
});
