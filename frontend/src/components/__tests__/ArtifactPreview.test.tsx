import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ArtifactPreview from '../ArtifactPreview';

const MARKDOWN = [
  '# Jane Doe',
  '',
  '## Core Competencies',
  '',
  '- Python',
  '',
  'Plain paragraph.',
].join('\n');

describe('ArtifactPreview', () => {
  it('renders markdown headings and list items when ready', () => {
    render(
      <ArtifactPreview status="ready" content={MARKDOWN} emptyMessage="Empty" />,
    );

    expect(screen.getByRole('heading', { name: 'Jane Doe' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Core Competencies' })).toBeTruthy();
    expect(screen.getByText('Python')).toBeTruthy();
    expect(screen.getByText('Plain paragraph.')).toBeTruthy();
  });

  it('shows source count and toolbar when ready', () => {
    const toolbar = <button>Generate Resume</button>;
    render(
      <ArtifactPreview
        status="ready"
        content={MARKDOWN}
        emptyMessage="Empty"
        sourceCount={3}
        toolbar={toolbar}
      />,
    );

    expect(screen.getByTestId('preview-source-count').textContent).toContain('3 sources rendered');
    expect(screen.getByText('Generate Resume')).toBeTruthy();
  });

  it('shows loading state', () => {
    render(
      <ArtifactPreview status="loading" content="" emptyMessage="Empty" />,
    );

    expect(screen.getByText('Rendering preview...')).toBeTruthy();
  });

  it('shows error state with retry callback', () => {
    const onRetry = vi.fn();
    render(
      <ArtifactPreview
        status="error"
        content=""
        emptyMessage="Empty"
        errorMessage="Preview exploded"
        onRetry={onRetry}
      />,
    );

    expect(screen.getByText('Preview exploded')).toBeTruthy();
    fireEvent.click(screen.getByText('Try again'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('shows empty state when idle or without content', () => {
    render(
      <ArtifactPreview status="idle" content="" emptyMessage="Select a template to preview." />,
    );

    expect(screen.getByText('Select a template to preview.')).toBeTruthy();
  });
});
