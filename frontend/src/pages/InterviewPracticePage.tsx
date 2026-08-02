import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { InterviewService } from '../services/InterviewService';
import { ProfileService } from '../services/ProfileService';
import type {
  AnswerEvaluation,
  InterviewFeedback,
  InterviewQuestionInstance,
  InterviewReport,
  InterviewSession,
  InterviewSummary,
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

const EVALUATION_DIMENSIONS: Array<{ key: keyof AnswerEvaluation; label: string }> = [
  { key: 'covers_claim', label: 'Covers the question claim' },
  { key: 'cites_evidence', label: 'Grounds the answer in evidence' },
  { key: 'matches_question_competencies', label: 'Aligns with the competencies' },
  { key: 'has_metric', label: 'Includes a measurable outcome' },
  { key: 'follows_structure', label: 'Follows a structured (STAR) answer' },
];

const MISSING_LABELS: Record<string, string> = {
  coverage: 'Coverage',
  evidence: 'Evidence',
  'measurable outcome': 'Measurable outcome',
  structure: 'STAR structure',
  consistency: 'Consistency',
};

const SUMMARY_ROWS: Array<{ key: keyof InterviewSummary; label: string }> = [
  { key: 'covered_claims', label: 'Claims covered' },
  { key: 'metric_citations', label: 'Measurable answers' },
  { key: 'evidence_citations', label: 'Evidence-backed' },
  { key: 'structured_answers', label: 'Structured answers' },
  { key: 'strong_answers', label: 'Strong answers' },
  { key: 'weak_answers', label: 'Weak answers' },
];

function categoryLabel(category: string): string {
  return category.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function missingLabel(signal: string): string {
  return MISSING_LABELS[signal] ?? signal;
}

export default function InterviewPracticePage() {
  const navigate = useNavigate();
  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [targetRole, setTargetRole] = useState('');
  const [status, setStatus] = useState<RequestStatus>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [question, setQuestion] = useState<InterviewQuestionInstance | null>(null);
  const [answerText, setAnswerText] = useState('');
  const [lastEvaluation, setLastEvaluation] = useState<AnswerEvaluation | null>(null);
  const [lastFeedback, setLastFeedback] = useState<InterviewFeedback | null>(null);
  const [report, setReport] = useState<InterviewReport | null>(null);
  const questionStartedAtRef = useRef<number>(Date.now());

  const service = InterviewService.getInstance();

  const loadProfiles = async () => {
    try {
      const list = await ProfileService.getInstance().getProfiles();
      setProfiles(list);
      if (list.length > 0) setSelectedProfileId(list[0].id);
    } catch {
      setErrorMessage('Unable to load profiles. Please ensure the backend is running.');
    }
  };

  useEffect(() => {
    loadProfiles();
  }, []);

  const begin = async () => {
    setStatus('starting');
    setErrorMessage('');
    try {
      const created = await service.createSession(selectedProfileId, targetRole.trim() || undefined);
      setSession(created);
      await advance(created);
    } catch (err) {
      setStatus('error');
      setErrorMessage(err instanceof Error ? err.message : 'Failed to start the interview');
    }
  };

  const advance = async (currentSession: InterviewSession) => {
    setStatus('advancing');
    setErrorMessage('');
    setLastEvaluation(null);
    setLastFeedback(null);
    setAnswerText('');
    try {
      const next = await service.nextStep(currentSession.id);
      setSession(next.session);
      if (next.completed) {
        setReport(next.report ?? null);
        setStatus('completed');
      } else if (next.question) {
        setQuestion(next.question);
        questionStartedAtRef.current = Date.now();
        setStatus('answering');
      } else {
        setStatus('error');
        setErrorMessage('The interview returned no question and was not completed.');
      }
    } catch (err) {
      setStatus('error');
      setErrorMessage(err instanceof Error ? err.message : 'Failed to advance the interview');
    }
  };

  const submitAnswer = async () => {
    if (!session || !question) return;
    setStatus('submitting');
    setErrorMessage('');
    try {
      const duration = Math.max(0, Math.round((Date.now() - questionStartedAtRef.current) / 1000));
      const result = await service.submitAnswer(session.id, answerText, duration);
      setSession(result.session);
      setLastEvaluation(result.answer.evaluation ?? null);
      setLastFeedback(result.answer.feedback ?? null);
      setStatus('evaluated');
    } catch (err) {
      setStatus('error');
      setErrorMessage(err instanceof Error ? err.message : 'Failed to submit the answer');
    }
  };

  const togglePause = async () => {
    if (!session) return;
    try {
      const updated =
        session.state === 'paused'
          ? await service.resumeSession(session.id)
          : await service.pauseSession(session.id);
      setSession(updated);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to update the interview state');
    }
  };

  const isBusy = status === 'starting' || status === 'submitting' || status === 'advancing';
  const isPaused = session?.state === 'paused';
  const canSubmit = status === 'answering' && answerText.trim().length > 0 && !isBusy && !isPaused;
  const canAdvance = status === 'evaluated' && !isBusy && !isPaused;

  const renderEvaluation = (evaluation: AnswerEvaluation, feedback: InterviewFeedback | null) => (
    <div className="mt-4 border border-emerald-200 bg-emerald-50 rounded-md p-4">
      <p className="text-xs font-semibold text-emerald-800 uppercase tracking-wide">
        Answer evaluation
      </p>
      <ul className="mt-3 space-y-1.5">
        {EVALUATION_DIMENSIONS.map(({ key, label }) => {
          const passed = evaluation[key] === true;
          return (
            <li key={key} className="flex items-center justify-between gap-3 text-sm">
              <span className="text-gray-700">{label}</span>
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                  passed ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                }`}
              >
                {passed ? 'Detected' : 'Not detected'}
              </span>
            </li>
          );
        })}
      </ul>
      {feedback && (
        <div className="mt-3 border-t border-emerald-200 pt-3">
          <p className="text-xs font-semibold text-emerald-800 uppercase tracking-wide">Feedback</p>
          {feedback.missing.length > 0 ? (
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <span className="text-xs text-gray-500">Missing:</span>
              {feedback.missing.map((signal) => (
                <span
                  key={signal}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800"
                >
                  {missingLabel(signal)}
                </span>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm text-emerald-800">No missing dimensions detected. Strong answer.</p>
          )}
          {feedback.improvement_recommendation && (
            <p className="mt-2 text-sm text-gray-700 leading-relaxed">
              {feedback.improvement_recommendation}
            </p>
          )}
        </div>
      )}
    </div>
  );

  const renderQuestion = (q: InterviewQuestionInstance) => (
    <div className="border border-gray-200 rounded-md bg-white p-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
          {categoryLabel(q.category)}
        </span>
        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-600">
          {q.difficulty}
        </span>
        <span className="text-xs text-gray-400">
          Question {q.order + 1} of {session?.questions.length ?? q.order + 1}
        </span>
      </div>
      <p className="mt-3 text-base font-medium text-gray-900">{q.question_text}</p>
      {q.suggested_answer && (
        <details className="mt-3">
          <summary className="cursor-pointer select-none text-xs font-semibold uppercase tracking-wide text-gray-500 hover:text-gray-700">
            Suggested answer outline
          </summary>
          <div className="mt-2.5 space-y-2 text-sm text-gray-700">
            {[
              ['Situation', q.suggested_answer.situation],
              ['Task', q.suggested_answer.task],
              ['Action', q.suggested_answer.action],
              ['Result', q.suggested_answer.result],
              ['Achievement', q.suggested_answer.achievement],
            ].map(
              ([label, value]) =>
                value && (
                  <div key={label}>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
                    <p className="mt-0.5 leading-relaxed">{value}</p>
                  </div>
                ),
            )}
          </div>
        </details>
      )}
    </div>
  );

  const renderReport = (r: InterviewReport) => (
    <div className="space-y-4">
      <div className="border border-gray-200 rounded-md bg-white p-5">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Interview Report</h3>
          <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
            {r.summary.answered_questions} of {r.summary.total_questions} answered
          </span>
        </div>
        <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-3">
          {SUMMARY_ROWS.map(({ key, label }) => (
            <div key={key} className="border border-gray-200 rounded-md p-3">
              <p className="text-lg font-semibold text-gray-900">{r.summary[key]}</p>
              <p className="text-xs text-gray-500">{label}</p>
            </div>
          ))}
        </div>
      </div>

      {r.strengths.length > 0 && (
        <div className="border border-green-200 bg-green-50 rounded-md p-4">
          <p className="text-xs font-semibold text-green-800 uppercase tracking-wide">Strengths</p>
          <ul className="mt-2 space-y-1.5">
            {r.strengths.map((item, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="mt-0.5 text-green-600" aria-hidden="true">✓</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {r.weaknesses.length > 0 && (
        <div className="border border-amber-200 bg-amber-50 rounded-md p-4">
          <p className="text-xs font-semibold text-amber-800 uppercase tracking-wide">Areas to improve</p>
          <ul className="mt-2 space-y-1.5">
            {r.weaknesses.map((item, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="mt-0.5 text-amber-600" aria-hidden="true">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {r.recommendations.length > 0 && (
        <div className="border border-blue-200 bg-blue-50 rounded-md p-4">
          <p className="text-xs font-semibold text-blue-800 uppercase tracking-wide">Recommended next steps</p>
          <ul className="mt-2 space-y-1.5">
            {r.recommendations.map((item, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="mt-0.5 text-blue-600" aria-hidden="true">→</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        onClick={() => navigate('/')}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-md transition-colors duration-200"
      >
        Back to Home
      </button>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Interview Practice</h1>
            <p className="text-sm text-gray-600 mt-1">Answer evidence-backed questions and get instant feedback</p>
          </div>
          {session && !isPaused && status !== 'completed' && (
            <button
              onClick={togglePause}
              className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Pause
            </button>
          )}
          {isPaused && (
            <button
              onClick={togglePause}
              className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
            >
              Resume
            </button>
          )}
        </div>
      </header>

      <main className="flex-1 px-6 py-8">
        <div className="max-w-3xl mx-auto space-y-6">
          {status === 'idle' && (
            <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Start a practice session</h2>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Profile</label>
                <select
                  value={selectedProfileId}
                  onChange={(e) => setSelectedProfileId(e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {profiles.length === 0 && <option value="">Loading profiles...</option>}
                  {profiles.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Target role (optional)</label>
                <input
                  type="text"
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  placeholder="e.g. Senior Platform Engineer"
                  className="w-full p-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button
                onClick={begin}
                disabled={!selectedProfileId}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-md transition-colors duration-200"
              >
                Start Interview
              </button>
            </div>
          )}

          {(status === 'starting' || status === 'advancing') && (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400">
              <svg className="animate-spin h-8 w-8 mb-3 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p className="text-sm">
                {status === 'starting' ? 'Building your interview plan...' : 'Loading next question...'}
              </p>
            </div>
          )}

          {question && (status === 'answering' || status === 'submitting' || status === 'evaluated' || status === 'error') && (
            <div className="space-y-4">
              {renderQuestion(question)}

              {status === 'answering' || status === 'submitting' || status === 'evaluated' ? (
                <div className="border border-gray-200 rounded-md bg-white p-5">
                  <label className="block text-sm font-medium text-gray-700 mb-1">Your answer</label>
                  <textarea
                    value={answerText}
                    onChange={(e) => setAnswerText(e.target.value)}
                    disabled={status === 'evaluated' || status === 'submitting'}
                    rows={6}
                    placeholder="Draft your answer here. Structure it around Situation, Task, Action, and Result..."
                    className="w-full p-3 border border-gray-300 rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500"
                  />
                  {isPaused && <p className="mt-2 text-sm text-amber-700">Session paused — resume to continue.</p>}
                  {!isPaused && canSubmit && (
                    <button
                      onClick={submitAnswer}
                      className="mt-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-md transition-colors duration-200"
                    >
                      Submit answer
                    </button>
                  )}
                  {lastEvaluation && renderEvaluation(lastEvaluation, lastFeedback)}
                </div>
              ) : null}

              {canAdvance && (
                <button
                  onClick={() => session && advance(session)}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2 px-4 rounded-md transition-colors duration-200"
                >
                  Next question
                </button>
              )}
            </div>
          )}

          {status === 'completed' && report && renderReport(report)}

          {status === 'error' && (
            <div className="bg-white border border-red-200 rounded-lg p-6 shadow-sm space-y-4">
              <p className="text-sm text-red-700">{errorMessage}</p>
              <button
                onClick={() => {
                  setStatus('idle');
                  setErrorMessage('');
                  setSession(null);
                  setQuestion(null);
                  setReport(null);
                }}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-md transition-colors duration-200"
              >
                Back to setup
              </button>
            </div>
          )}
        </div>
      </main>

      <footer className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <button
            onClick={() => navigate('/')}
            className="text-sm text-blue-600 hover:underline"
          >
            ← Back to Home
          </button>
          <span className="text-sm text-gray-600">Deterministic evaluation — no AI scoring</span>
        </div>
      </footer>
    </div>
  );
}
