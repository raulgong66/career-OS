import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { InterviewService } from '../services/InterviewService';
import { ProfileService } from '../services/ProfileService';
import type {
  AnswerEvaluation,
  InterviewFeedback,
  InterviewQuestionInstance,
  InterviewReport,
  InterviewSession,
  ProfileSummary,
} from '../types';

type RequestStatus =
  | 'idle'
  | 'starting'
  | 'answering'
  | 'submitting'
  | 'evaluated'
  | 'advancing'
  | 'completed'
  | 'error';

const SEVERITY_STYLES: Record<string, string> = {
  info: 'bg-blue-100 text-blue-800',
  warning: 'bg-amber-100 text-amber-800',
  error: 'bg-red-100 text-red-800',
};

function categoryLabel(category: string): string {
  return category.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function scoreColor(score: number): string {
  if (score >= 80) return 'text-green-700';
  if (score >= 50) return 'text-amber-700';
  return 'text-red-700';
}

function renderFeedback(feedback: InterviewFeedback[]) {
  if (feedback.length === 0) {
    return <p className="text-sm text-gray-600">No feedback signals were returned.</p>;
  }
  return (
    <ul className="space-y-2">
      {feedback.map((item) => (
        <li key={item.code} className="flex items-start gap-2 text-sm">
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_STYLES[item.severity] ?? SEVERITY_STYLES.info}`}
          >
            {item.severity}
          </span>
          <span className="text-gray-700">{item.message}</span>
        </li>
      ))}
    </ul>
  );
}

export default function InterviewPracticePage() {
  const navigate = useNavigate();
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const [status, setStatus] = useState<RequestStatus>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [question, setQuestion] = useState<InterviewQuestionInstance | null>(null);
  const [answerText, setAnswerText] = useState('');
  const [lastEvaluation, setLastEvaluation] = useState<AnswerEvaluation | null>(null);
  const [report, setReport] = useState<InterviewReport | null>(null);

  useEffect(() => {
    ProfileService.getInstance()
      .getProfiles()
      .then((list) => {
        setProfiles(list);
        if (list.length > 0) setSelectedProfileId(list[0].id);
      })
      .catch(() => {
        setErrorMessage('Unable to load profiles. Please ensure the backend is running.');
      })
      .finally(() => setLoadingProfiles(false));
  }, []);

  const resetForNewSession = () => {
    setStatus('idle');
    setErrorMessage('');
    setSession(null);
    setQuestion(null);
    setLastEvaluation(null);
    setReport(null);
    setAnswerText('');
  };

  const startInterview = async () => {
    if (!selectedProfileId) return;
    setStatus('starting');
    setErrorMessage('');
    try {
      const canonical = await ProfileService.getInstance().getCanonicalProfile(selectedProfileId);
      const created = await InterviewService.getInstance().createSession(canonical);
      setSession(created);
      setQuestion(created.current_question);
      setStatus(created.current_question ? 'answering' : 'completed');
    } catch (err) {
      setStatus('error');
      setErrorMessage(err instanceof Error ? err.message : 'Failed to start the interview');
    }
  };

  const submitAnswer = async () => {
    if (!session || !question) return;
    setStatus('submitting');
    setErrorMessage('');
    try {
      const result = await InterviewService.getInstance().submitAnswer(
        session.session_id,
        question.question.id,
        answerText,
        question.question.evidence_citations,
      );
      setSession(result.session);
      setLastEvaluation(result.evaluation);
      setStatus('evaluated');
    } catch (err) {
      setStatus('error');
      setErrorMessage(err instanceof Error ? err.message : 'Failed to submit the answer');
    }
  };

  const advance = async () => {
    if (!session) return;
    setStatus('advancing');
    setErrorMessage('');
    setLastEvaluation(null);
    setAnswerText('');
    try {
      const result = await InterviewService.getInstance().nextStep(session.session_id);
      setSession(result.session);
      if (result.completed) {
        setQuestion(null);
        setReport(result.report ?? null);
        setStatus('completed');
      } else {
        setQuestion(result.next_question);
        setStatus('answering');
      }
    } catch (err) {
      setStatus('error');
      setErrorMessage(err instanceof Error ? err.message : 'Failed to advance the interview');
    }
  };

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId) ?? null;
  const isBusy = status === 'starting' || status === 'submitting' || status === 'advancing';
  const canSubmit = status === 'answering' && answerText.trim().length > 0 && !isBusy;
  const canAdvance = status === 'evaluated' && !isBusy;

  const renderStartPanel = () => (
    <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Interview Preparation</h2>
          <p className="text-sm text-gray-600 mt-1">
            Practice with a deterministic, evidence-backed interview built from a canonical profile.
          </p>
        </div>
        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
          READY
        </span>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Profile</label>
          <select
            value={selectedProfileId}
            onChange={(e) => setSelectedProfileId(e.target.value)}
            disabled={loadingProfiles}
            className="w-full p-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {loadingProfiles && <option value="">Loading profiles...</option>}
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        {selectedProfile && (
          <div className="border border-gray-200 rounded-md divide-y divide-gray-200">
            <div className="px-3 py-2">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Headline</label>
              <p className="mt-0.5 text-sm text-gray-700">{selectedProfile.headline || '—'}</p>
            </div>
            <div className="px-3 py-2">
              <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Artifacts</label>
              <p className="mt-0.5 text-sm text-gray-700">
                {selectedProfile.artifactCount} artifact{(selectedProfile.artifactCount !== 1 ? 's' : '')} defined
              </p>
            </div>
          </div>
        )}
        <button
          onClick={startInterview}
          disabled={!selectedProfileId || isBusy}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-md transition-colors duration-200"
        >
          Start Interview
        </button>
      </div>
    </div>
  );

  const renderBusy = (label: string) => (
    <div className="flex flex-col items-center justify-center py-12 text-gray-400">
      <svg className="animate-spin h-8 w-8 mb-3 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <p className="text-sm">{label}</p>
    </div>
  );

  const renderProgress = (current: InterviewSession) => (
    <div className="flex items-center gap-3 text-sm text-gray-600">
      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700">
        {current.state.replace(/_/g, ' ')}
      </span>
      <span>
        Answered {current.answered_count} of {current.question_count} questions
      </span>
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 transition-all duration-300"
          style={{
            width: `${current.question_count > 0 ? (current.answered_count / current.question_count) * 100 : 0}%`,
          }}
        ></div>
      </div>
    </div>
  );

  const renderQuestionCard = (q: InterviewQuestionInstance) => (
    <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
          {categoryLabel(q.question.category)}
        </span>
        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700">
          {q.question.difficulty}
        </span>
        <span className="text-xs text-gray-500">
          Question {q.index} of {q.total}
        </span>
      </div>
      <p className="text-lg font-medium text-gray-900 leading-relaxed">{q.question.text}</p>
      {q.question.evidence_citations.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Evidence references</p>
          <div className="flex flex-wrap gap-1.5">
            {q.question.evidence_citations.map((ref) => (
              <span
                key={`${ref.type}:${ref.id}`}
                className="inline-flex items-center px-2.5 py-1 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
              >
                {ref.type}:{ref.id}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderEvaluation = (evaluation: AnswerEvaluation) => (
    <div className="bg-white border border-emerald-200 rounded-lg p-6 shadow-sm">
      <p className="text-xs font-semibold text-emerald-800 uppercase tracking-wide mb-4">Answer evaluation</p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { key: 'overall_score', label: 'Overall' },
          { key: 'coverage_score', label: 'Coverage' },
          { key: 'evidence_score', label: 'Evidence' },
          { key: 'structure_score', label: 'Structure' },
        ].map(({ key, label }) => {
          const score = evaluation[key as keyof AnswerEvaluation] as number;
          return (
            <div key={key} className="border border-gray-200 rounded-md p-3 text-center">
              <p className={`text-2xl font-bold ${scoreColor(score)}`}>{score}</p>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mt-1">{label}</p>
            </div>
          );
        })}
      </div>
      <div className="mt-4 border-t border-emerald-200 pt-4">
        <p className="text-xs font-semibold text-emerald-800 uppercase tracking-wide mb-2">Feedback</p>
        {renderFeedback(evaluation.feedback)}
      </div>
      <div className="mt-4 flex justify-end">
        <button
          onClick={advance}
          disabled={!canAdvance}
          className="inline-flex items-center px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors duration-200"
        >
          Next Question
        </button>
      </div>
    </div>
  );

  const renderReport = (current: InterviewReport) => (
    <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Interview Summary</h2>
          <p className="text-sm text-gray-600 mt-1">Deterministic report generated by the backend.</p>
        </div>
        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
          COMPLETED
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="border border-gray-200 rounded-md p-4 text-center">
          <p className={`text-3xl font-bold ${scoreColor(current.summary.average_score)}`}>
            {current.summary.average_score}
          </p>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mt-1">Average score</p>
        </div>
        <div className="border border-gray-200 rounded-md p-4 text-center">
          <p className="text-3xl font-bold text-gray-900">{current.summary.question_count}</p>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mt-1">Questions</p>
        </div>
        <div className="border border-gray-200 rounded-md p-4 text-center">
          <p className="text-3xl font-bold text-gray-900">{current.summary.answered_questions}</p>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mt-1">Answered</p>
        </div>
      </div>

      <div className="mt-5 border-t border-gray-200 pt-4">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Feedback</p>
        {renderFeedback(current.summary.feedback)}
      </div>

      <div className="mt-5 flex gap-3">
        <button
          onClick={resetForNewSession}
          className="inline-flex items-center px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm transition-colors duration-200"
        >
          Start a new interview
        </button>
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center px-4 py-2 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 font-semibold text-sm transition-colors duration-200"
        >
          Back to Home
        </button>
      </div>
    </div>
  );

  const renderError = () => (
    <div className="bg-white border border-red-200 rounded-lg p-6 shadow-sm">
      <p className="text-sm font-semibold text-red-700 mb-2">Something went wrong</p>
      <p className="text-sm text-gray-700 mb-4">{errorMessage}</p>
      <div className="flex gap-3">
        {session ? (
          <button
            onClick={() => setStatus(question && lastEvaluation ? 'evaluated' : 'answering')}
            className="inline-flex items-center px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm transition-colors duration-200"
          >
            Try again
          </button>
        ) : (
          <button
            onClick={resetForNewSession}
            className="inline-flex items-center px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm transition-colors duration-200"
          >
            Back to profile selection
          </button>
        )}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-8">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-gray-900">CareerOS Platform Alpha</h1>
            <p className="text-lg text-gray-600 mt-2">Interview Preparation</p>
          </div>
          <button
            onClick={() => navigate('/')}
            className="text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            ← Back to Home
          </button>
        </div>
      </header>

      <main className="flex-1 px-6 py-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {errorMessage && status !== 'error' && (
            <div className="border border-red-200 bg-red-50 rounded-md p-4 text-sm text-red-700">{errorMessage}</div>
          )}

          {status === 'idle' && renderStartPanel()}
          {status === 'starting' && renderBusy('Starting interview...')}
          {status === 'advancing' && renderBusy('Advancing...')}

          {session && status !== 'idle' && status !== 'error' && renderProgress(session)}

          {question && (status === 'answering' || status === 'submitting' || status === 'evaluated') && (
            <>
              {renderQuestionCard(question)}
              {(status === 'answering' || status === 'submitting') && (
                <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Your answer</label>
                  <textarea
                    value={answerText}
                    onChange={(e) => setAnswerText(e.target.value)}
                    disabled={isBusy}
                    rows={6}
                    placeholder="Describe how you handled this situation, what you did, and the measurable outcome..."
                    className="w-full p-3 border border-gray-300 rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
                  />
                  <div className="mt-4 flex justify-end">
                    <button
                      onClick={submitAnswer}
                      disabled={!canSubmit}
                      className="inline-flex items-center px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors duration-200"
                    >
                      Submit Answer
                    </button>
                  </div>
                </div>
              )}
              {status === 'evaluated' && lastEvaluation && renderEvaluation(lastEvaluation)}
            </>
          )}

          {status === 'completed' && report && renderReport(report)}
          {status === 'completed' && !report && (
            <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
              <p className="text-sm text-gray-700">
                The interview is complete, but the backend did not return a report.
              </p>
              <button
                onClick={resetForNewSession}
                className="mt-4 inline-flex items-center px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm transition-colors duration-200"
              >
                Start a new interview
              </button>
            </div>
          )}

          {status === 'error' && renderError()}
        </div>
      </main>

      <footer className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <span className="text-sm text-gray-600">Platform Alpha · Interview Preparation</span>
          <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
            Demo Ready
          </span>
        </div>
      </footer>
    </div>
  );
}
