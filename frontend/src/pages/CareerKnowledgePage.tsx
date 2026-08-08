import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CareerKnowledgeService } from '../services/CareerKnowledgeService';
import type { KnowledgeAnswer } from '../types';

const exampleQuestions = [
  'What is CareerOS?',
  'How is AI applied?',
  'How does artifact generation work?',
  'Explain the Resolution Engine',
];

const knowledgeTopics = [
  'CareerOS',
  'Artifact Generation',
  'AI',
  'Reasoning',
  'Resolution',
  'Interview',
  'Profile Management',
];

export default function CareerKnowledgePage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<KnowledgeAnswer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAsk = async () => {
    const question = query.trim();
    if (!question || loading) return;

    setLoading(true);
    setError('');

    try {
      const service = CareerKnowledgeService.getInstance();
      const answer = await service.ask(question);
      setResult(answer);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to query Career Knowledge');
    } finally {
      setLoading(false);
    }
  };

  const confidencePercent = result ? Math.round(result.confidence * 100) : 0;

  return (
    <div className="min-h-screen bg-blue-50 flex flex-col">
      <header className="bg-white border-b border-blue-100 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">CareerOS Platform Alpha</h1>
          <p className="text-sm text-gray-600 mt-1">Career Knowledge</p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="text-sm font-medium text-blue-600 hover:text-blue-800"
        >
          ← Back to Home
        </button>
      </header>

      <main className="flex-1 px-6 py-12">
        <div className="max-w-4xl mx-auto space-y-8">
          <section className="bg-white border border-blue-100 rounded-lg p-8 shadow-sm">
            <h2 className="text-3xl font-bold text-gray-900">Career Knowledge</h2>
            <p className="text-sm font-medium text-blue-600 mt-2">
              Powered by the Career Self Knowledge System
            </p>
            <p className="text-base text-gray-600 mt-4">Ask CareerOS about itself.</p>

            <div className="flex items-center gap-3 mt-6">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. What is CareerOS?"
                className="flex-1 block w-full rounded-md border border-blue-200 bg-white px-4 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={handleAsk}
                disabled={loading || !query.trim()}
                className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-md transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Ask
              </button>
            </div>
            {loading && (
              <p className="mt-3 text-sm text-blue-600">Asking CareerOS...</p>
            )}

            <div className="mt-6">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Try asking</p>
              <ul className="mt-3 space-y-2 list-disc list-inside">
                {exampleQuestions.map((q) => (
                  <li key={q} className="text-sm text-gray-700">
                    <button
                      type="button"
                      onClick={() => setQuery(q)}
                      className="text-blue-700 hover:text-blue-900 hover:underline"
                    >
                      {q}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="bg-white border border-blue-100 rounded-lg p-8 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900">Knowledge Explorer</h3>
            <div className="mt-4 flex flex-wrap gap-2">
              {knowledgeTopics.map((topic) => (
                <button
                  key={topic}
                  type="button"
                  onClick={() => setQuery(topic)}
                  className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-50 text-blue-700 border border-blue-100 hover:bg-blue-100 transition-colors duration-200"
                >
                  {topic}
                </button>
              ))}
            </div>
          </section>

          {error && (
            <div
              className="border border-red-200 bg-red-50 rounded-md p-4 text-sm text-red-700"
              role="alert"
            >
              {error}
            </div>
          )}

          <section className="bg-white border border-blue-100 rounded-lg p-8 shadow-sm space-y-8">
            <div>
              <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Answer</h4>
              {result ? (
                <p className="mt-2 text-sm text-gray-800 whitespace-pre-wrap">{result.answer}</p>
              ) : (
                <p className="mt-2 text-sm text-gray-400">Answer will appear here.</p>
              )}
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Sources</h4>
              {result ? (
                result.citations.length > 0 ? (
                  <ul className="mt-2 space-y-2">
                    {result.citations.map((citation, index) => (
                      <li key={index} className="text-sm text-gray-700">
                        <span className="font-mono text-blue-700">
                          {citation.file}:{citation.line_start}
                        </span>
                        {citation.text && (
                          <span className="ml-2 text-gray-500">{citation.text}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-gray-400">No sources returned.</p>
                )
              ) : (
                <p className="mt-2 text-sm text-gray-400">Sources will appear here.</p>
              )}
            </div>
            <div>
              <h4 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Confidence</h4>
              {result ? (
                <div className="mt-2">
                  <p className="text-sm font-semibold text-gray-800">{confidencePercent}%</p>
                  <div className="mt-2 h-2 w-48 rounded-full bg-blue-100">
                    <div
                      className="h-2 rounded-full bg-blue-600"
                      style={{ width: `${confidencePercent}%` }}
                    />
                  </div>
                </div>
              ) : (
                <p className="mt-2 text-sm text-gray-400">—</p>
              )}
            </div>
          </section>
        </div>
      </main>

      <footer className="bg-white border-t border-blue-100 px-6 py-4">
        <div className="max-w-6xl mx-auto">
          <span className="text-sm text-gray-600">Platform Alpha</span>
        </div>
      </footer>
    </div>
  );
}
