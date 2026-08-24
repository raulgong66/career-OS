import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { TransformationPhase, TransformationPlan } from '../types';
import { TransformationService } from '../services/TransformationService';

type Phase = 'input' | 'plan' | 'confirmed';

const TRANSFORMATION_FLOW = [
  'Client objective',
  'Proposed transformation',
  'Human confirmation',
  'Phase selection',
  'Handoff to Mission evaluation',
];

export default function TransformationPage() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>('input');
  const [objectiveText, setObjectiveText] = useState('');
  const [plan, setPlan] = useState<TransformationPlan | null>(null);
  const [selectedPhaseNumber, setSelectedPhaseNumber] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const handleInterpret = async () => {
    if (!objectiveText.trim()) return;
    setBusy(true);
    setError('');
    try {
      const result = await TransformationService.getInstance().interpret(objectiveText.trim());
      setPlan(result);
      setPhase('plan');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to interpret transformation objective.');
    } finally {
      setBusy(false);
    }
  };

  const handleConfirm = () => {
    setPhase('confirmed');
  };

  const handleSelectPhase = (phaseNumber: number) => {
    setSelectedPhaseNumber(phaseNumber);
  };

  const handleHandoffToMission = () => {
    if (!plan || selectedPhaseNumber === null) return;
    const selected = plan.phases.find((p) => p.phase_number === selectedPhaseNumber);
    if (!selected) return;
    navigate('/mission', { state: { contract: selected.contract } });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !busy && objectiveText.trim()) {
      e.preventDefault();
      handleInterpret();
    }
  };

  const handleReset = () => {
    setPhase('input');
    setObjectiveText('');
    setPlan(null);
    setSelectedPhaseNumber(null);
    setError('');
  };

  const selectedPhase = plan?.phases.find((p) => p.phase_number === selectedPhaseNumber) ?? null;

  return (
    <div className="min-h-screen bg-[#F5F9FF]">
      {/* Header */}
      <header className="bg-primary-900 px-6 xl:px-10 2xl:px-16 pt-10 pb-10">
        <div className="max-w-none">
          <div className="flex items-center justify-between flex-wrap gap-3 mb-4 animate-[fade-in-up_0.6s_ease-out_both]">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold text-white bg-white/15 backdrop-blur-sm border border-white/25">
              Transformation Mission
            </span>
          </div>
          <h1 className="text-4xl font-bold text-white tracking-tight max-w-2xl">
            Transformation Mission
          </h1>
          <p className="text-lg text-blue-100 mt-3">
            Decompose a client business objective into evaluable transformation phases
          </p>
        </div>
      </header>

      <main className="px-6 xl:px-10 2xl:px-16 py-10 max-w-none">
        {/* Flow breadcrumb */}
        <div className="mb-10 flex flex-wrap gap-2">
          {TRANSFORMATION_FLOW.map((label, idx) => {
            const isActive =
              (phase === 'input' && idx === 0) ||
              (phase === 'plan' && idx === 1) ||
              (phase === 'confirmed' && (idx === 2 || idx === 3 || idx === 4));
            const isPast =
              (phase === 'plan' && idx === 0) ||
              (phase === 'confirmed' && idx <= 2);
            return (
              <span
                key={label}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : isPast
                    ? 'bg-blue-100 text-blue-600'
                    : 'bg-gray-100 text-gray-400'
                }`}
              >
                {idx + 1}. {label}
              </span>
            );
          })}
        </div>

        {/* Phase: Input */}
        {phase === 'input' && (
          <div className="max-w-3xl">
            <div className="bg-white rounded-xl border border-blue-100 shadow-sm p-8">
              <h2 className="text-xl font-bold text-gray-900 mb-2">Client Business Objective</h2>
              <p className="text-sm text-gray-500 mb-6">
                Describe the client's business objective. CareerOS will decompose it into 3-5
                sequential transformation phases, each independently evaluable against your
                candidate pool.
              </p>
              <textarea
                value={objectiveText}
                onChange={(e) => setObjectiveText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g. Build a production-grade data platform for real-time analytics on AWS for a healthcare client with HIPAA compliance requirements..."
                className="w-full h-40 px-4 py-3 border border-gray-200 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
                disabled={busy}
              />
              {error && (
                <p className="mt-3 text-sm text-red-600">{error}</p>
              )}
              <div className="mt-6 flex justify-end">
                <button
                  onClick={handleInterpret}
                  disabled={busy || !objectiveText.trim()}
                  className="bg-gradient-to-r from-blue-600 to-blue-400 hover:from-blue-700 hover:to-blue-500 text-white font-semibold py-2.5 px-6 rounded-lg shadow-md shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                >
                  {busy ? 'Interpreting...' : 'Generate Transformation Plan'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Phase: Plan review / Confirmation */}
        {phase === 'plan' && plan && (
          <div className="max-w-4xl space-y-8">
            <div className="bg-white rounded-xl border border-blue-100 shadow-sm p-8">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">Proposed Transformation Plan</h2>
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                  {plan.phases.length} phases
                </span>
              </div>
              <p className="text-sm text-gray-600 mb-6 leading-relaxed">{plan.summary}</p>

              {plan.constraints.length > 0 && (
                <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-100">
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Cross-Phase Constraints
                  </h3>
                  <ul className="space-y-1">
                    {plan.constraints.map((c, i) => (
                      <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                        <span className="text-gray-400 mt-0.5">-</span>
                        {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="space-y-4">
                {plan.phases.map((p) => (
                  <PhaseCard key={p.phase_id} phase={p} />
                ))}
              </div>

              <div className="mt-8 p-4 bg-amber-50 rounded-lg border border-amber-200">
                <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1">
                  Human Review Required
                </p>
                <p className="text-sm text-amber-800">
                  This plan is AI-proposed and must be reviewed by a human before proceeding.
                  Verify that the phases match the client's actual business objectives and that
                  the sequencing is appropriate.
                </p>
              </div>

              <div className="mt-6 flex justify-end gap-3">
                <button
                  onClick={handleReset}
                  className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors"
                >
                  Start Over
                </button>
                <button
                  onClick={handleConfirm}
                  className="bg-gradient-to-r from-blue-600 to-blue-400 hover:from-blue-700 hover:to-blue-500 text-white font-semibold py-2.5 px-6 rounded-lg shadow-md shadow-blue-600/20 transition-all duration-200"
                >
                  Confirm Plan
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Phase: Confirmed - select phase */}
        {phase === 'confirmed' && plan && (
          <div className="max-w-4xl space-y-8">
            <div className="bg-white rounded-xl border border-blue-100 shadow-sm p-8">
              <h2 className="text-xl font-bold text-gray-900 mb-2">Select a Phase to Evaluate</h2>
              <p className="text-sm text-gray-500 mb-6">
                Choose one phase to evaluate against your candidate pool. Each phase is an
                independent mission with its own requirements and role.
              </p>

              <div className="space-y-3">
                {plan.phases.map((p) => (
                  <button
                    key={p.phase_id}
                    onClick={() => handleSelectPhase(p.phase_number)}
                    className={`w-full text-left p-4 rounded-lg border-2 transition-all duration-200 ${
                      selectedPhaseNumber === p.phase_number
                        ? 'border-blue-500 bg-blue-50 shadow-md'
                        : 'border-gray-100 bg-white hover:border-blue-200 hover:bg-blue-50/50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                          selectedPhaseNumber === p.phase_number
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-500'
                        }`}
                      >
                        {p.phase_number}
                      </span>
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-semibold text-gray-900">{p.title}</h3>
                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{p.description}</p>
                      </div>
                      <div className="flex-shrink-0 text-xs text-gray-400">
                        {p.contract.requirements.length} requirement{p.contract.requirements.length !== 1 ? 's' : ''}
                      </div>
                    </div>
                  </button>
                ))}
              </div>

              {selectedPhase && (
                <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
                  <h3 className="text-sm font-semibold text-blue-900 mb-2">
                    Selected: Phase {selectedPhase.phase_number} — {selectedPhase.title}
                  </h3>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="font-medium text-blue-700">Role:</span>{' '}
                      <span className="text-blue-800">{selectedPhase.contract.role}</span>
                    </div>
                    <div>
                      <span className="font-medium text-blue-700">Requirements:</span>{' '}
                      <span className="text-blue-800">{selectedPhase.contract.requirements.length}</span>
                    </div>
                  </div>
                  {selectedPhase.contract.requirements.length > 0 && (
                    <div className="mt-2">
                      <ul className="space-y-0.5">
                        {selectedPhase.contract.requirements.map((r, i) => (
                          <li key={i} className="text-xs text-blue-700 flex items-start gap-1.5">
                            <span className="text-blue-400 mt-0.5">-</span>
                            {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              <div className="mt-6 flex justify-end gap-3">
                <button
                  onClick={() => setPhase('plan')}
                  className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors"
                >
                  Back
                </button>
                <button
                  onClick={handleHandoffToMission}
                  disabled={selectedPhaseNumber === null}
                  className="bg-gradient-to-r from-blue-600 to-blue-400 hover:from-blue-700 hover:to-blue-500 text-white font-semibold py-2.5 px-6 rounded-lg shadow-md shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                >
                  Evaluate Phase {selectedPhaseNumber ?? ''} →
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function PhaseCard({ phase }: { phase: TransformationPhase }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="border border-gray-100 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 hover:bg-gray-50 transition-colors flex items-center gap-3"
      >
        <span className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-bold">
          {phase.phase_number}
        </span>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-gray-900">{phase.title}</h3>
          {!expanded && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{phase.description}</p>
          )}
        </div>
        <span className="text-xs text-gray-400 flex-shrink-0">
          {expanded ? '▲' : '▼'}
        </span>
      </button>
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-50 pt-3 space-y-3">
          <p className="text-sm text-gray-600 leading-relaxed">{phase.description}</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="text-xs">
              <span className="font-medium text-gray-500">Role:</span>{' '}
              <span className="text-gray-700">{phase.contract.role}</span>
            </div>
            <div className="text-xs">
              <span className="font-medium text-gray-500">Requirements:</span>{' '}
              <span className="text-gray-700">{phase.contract.requirements.length}</span>
            </div>
          </div>
          {phase.contract.requirements.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 mb-1">Requirements</h4>
              <ul className="space-y-0.5">
                {phase.contract.requirements.map((r, i) => (
                  <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                    <span className="text-gray-400 mt-0.5">-</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {phase.contract.capabilities.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 mb-1">Capabilities</h4>
              <div className="flex flex-wrap gap-1.5">
                {phase.contract.capabilities.map((c, i) => (
                  <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}
          {phase.contract.constraints.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 mb-1">Phase Constraints</h4>
              <ul className="space-y-0.5">
                {phase.contract.constraints.map((c, i) => (
                  <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                    <span className="text-gray-400 mt-0.5">-</span>
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
