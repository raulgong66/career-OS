import type { ReactNode } from 'react';

export type PreviewStatus = 'idle' | 'loading' | 'ready' | 'error';

function renderMarkdown(content: string) {
  const lines = content.split('\n');
  return lines.map((line, index) => {
    if (line.startsWith('### ')) {
      return <h5 key={index} className="text-sm font-semibold text-gray-900 mt-3 mb-1">{line.slice(4)}</h5>;
    }
    if (line.startsWith('## ')) {
      return <h4 key={index} className="text-base font-semibold text-gray-900 mt-4 mb-1.5">{line.slice(3)}</h4>;
    }
    if (line.startsWith('# ')) {
      return <h3 key={index} className="text-lg font-bold text-gray-900 mt-5 mb-2">{line.slice(2)}</h3>;
    }
    if (line.startsWith('- ')) {
      return <li key={index} className="text-sm text-gray-700 ml-5">{line.slice(2)}</li>;
    }
    if (line.trim()) {
      return <p key={index} className="text-sm text-gray-700 mb-1.5 leading-relaxed">{line}</p>;
    }
    return <div key={index} className="h-2" />;
  });
}

interface ArtifactPreviewProps {
  status: PreviewStatus;
  content: string;
  emptyMessage: string;
  errorMessage?: string;
  sourceCount?: number | null;
  toolbar?: ReactNode;
  onRetry?: () => void;
}

export default function ArtifactPreview({
  status,
  content,
  emptyMessage,
  errorMessage,
  sourceCount,
  toolbar,
  onRetry,
}: ArtifactPreviewProps) {
  if (status === 'loading') {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <svg className="animate-spin h-8 w-8 mb-3 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p className="text-sm">Rendering preview...</p>
      </div>
    );
  }
  if (status === 'error') {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-sm text-red-700 mb-3">{errorMessage || 'Failed to render preview.'}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="inline-flex items-center px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm transition-colors duration-200"
            >
              Try again
            </button>
          )}
        </div>
      </div>
    );
  }
  if (status === 'idle' || content === '') {
    return (
      <div className="flex items-center justify-center h-64 text-sm text-gray-400">
        {emptyMessage}
      </div>
    );
  }
  return (
    <div>
      {toolbar && <div className="flex flex-wrap items-center justify-between gap-3 mb-4">{toolbar}</div>}
      {typeof sourceCount === 'number' && (
        <p className="text-xs text-gray-500 mb-3" data-testid="preview-source-count">
          {sourceCount} sources rendered
        </p>
      )}
      <div className="space-y-1">{renderMarkdown(content)}</div>
    </div>
  );
}
