import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import CareerKnowledgePage from '../CareerKnowledgePage';

function renderPage() {
  return render(
    <MemoryRouter>
      <CareerKnowledgePage />
    </MemoryRouter>
  );
}

describe('CareerKnowledgePage', () => {
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

  it('renders the Knowledge Explorer topics', () => {
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
      expect(screen.getByText(topic)).toBeTruthy();
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
});
