import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type {
  MissionCandidateEvaluation,
  MissionContract,
  MissionEvaluationResult,
  MissionStatus,
  RequirementCoverage,
} from '../types';
import { MissionService } from '../services/MissionService';
import { ProfileService } from '../services/ProfileService';

type Phase = 'input' | 'review' | 'candidate' | 'evaluating' | 'results' | 'team';

const MISSION_PROMPT = 'What are you trying to accomplish?';

const MISSION_FLOW = [
  'Business challenge',
  'Mission Contract',
  'Human confirmation',
  'CareerOS evaluation',
  'Review evidence',
  'Select people for the mission team',
  'Proposed Mission Team',
];

const STATUS_LABELS: Record<MissionStatus, string> = {
  evidence_backed: 'Evidence-backed',
  partial_evidence: 'Partial evidence',
  evidence_gaps: 'Evidence gaps',
  no_requirements: 'No requirements met',
};

const STATUS_STYLES: Record<MissionStatus, string> = {
  evidence_backed: 'bg-green-100 text-green-700',
  partial_evidence: 'bg-yellow-100 text-yellow-800',
  evidence_gaps: 'bg-orange-100 text-orange-700',
  no_requirements: 'bg-gray-100 text-gray-600',
};

const REQUIREMENT_LABELS: Record<RequirementCoverage['status'], string> = {
  evidenced: 'Evidenced',
  referenced_without_evidence: 'Referenced, not evidenced',
  gap: 'Evidence gap',
};

const REQUIREMENT_STYLES: Record<RequirementCoverage['status'], string> = {
  evidenced: 'bg-green-50 text-green-700 border-green-200',
  referenced_without_evidence: 'bg-yellow-50 text-yellow-800 border-yellow-200',
  gap: 'bg-red-50 text-red-600 border-red-200',
};

const TEAM_NOTE =
  'Team selection is a human decision. CareerOS provides the evidence and limitations for each candidate; it does not automatically certify the proposed team.';

function SectionCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-white rounded-xl border border-blue-100 shadow-sm p-8">
      <h2 className="text-xl font-bold text-gray-900 mb-4">{title}</h2>
      {children}
    </section>
  );
}

function ResultDetail({ result }: { result: MissionEvaluationResult }) {
  return (
    <div>
      <p className="text-sm text-gray-600 mt-3">{result.message}</p>

      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-lg border border-blue-100 bg-blue-50/50 p-4">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Text match
          </p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {result.text_coverage.toFixed(1)}%
          </p>
        </div>
        <div className="rounded-lg border border-blue-100 bg-blue-50/50 p-4">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Evidence-backed
          </p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {result.evidence_backed_coverage.toFixed(1)}%
          </p>
        </div>
      </div>

      <div className="mt-6">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">
          Requirement coverage
        </h4>
        <ul className="space-y-2">
          {result.requirements.map((row) => (
            <li
              key={row.requirement}
              className={`flex items-center justify-between gap-3 rounded-lg border px-4 py-2 text-sm ${REQUIREMENT_STYLES[row.status]}`}
            >
              <span className="font-medium">{row.requirement}</span>
              <span className="text-xs font-semibold">
                {REQUIREMENT_LABELS[row.status]}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-6">
        <h4 className="text-sm font-semibold text-gray-700 mb-3">
          Evidence-backed recommendations ({result.recommendations.length})
        </h4>
        <ul className="space-y-2">
          {result.recommendations.map((rec) => (
            <li key={rec.id} className="rounded-lg border border-blue-100 p-4 text-sm">
              <p className="font-semibold text-gray-800">{rec.displayName}</p>
              <p className="text-gray-500 mt-1">
                {rec.type} &middot; {rec.operation} &middot; {rec.evidence.length}{' '}
                evidence item
                {rec.evidence.length !== 1 ? 's' : ''}
              </p>
            </li>
          ))}
          {result.recommendations.length === 0 && (
            <li className="text-sm text-gray-500">None.</li>
          )}
        </ul>
      </div>

      <p className="mt-6 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm p-4">
        Human review is required before this mission can be acted on.
      </p>
    </div>
  );
}

export default function MissionPage() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>('input');
  const [missionText, setMissionText] = useState('');
  const [profiles, setProfiles] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedProfileIds, setSelectedProfileIds] = useState<string[]>([]);
  const [contract, setContract] = useState<MissionContract | null>(null);
  const [results, setResults] = useState<MissionCandidateEvaluation[]>([]);
  const [teamSelection, setTeamSelection] = useState<Record<string, boolean>>({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    ProfileService.getInstance()
      .getProfiles()
      .then((all) => {
        setProfiles(all.map((p) => ({ id: p.id, name: p.name })));
      })
      .catch(() => {
        setProfiles([]);
      });
  }, []);

  const toggleProfile = (profileId: string) => {
    setSelectedProfileIds((current) =>
      current.includes(profileId)
        ? current.filter((id) => id !== profileId)
        : [...current, profileId],
    );
  };

  const toggleTeamSelection = (profileId: string) => {
    setTeamSelection((current) => ({ ...current, [profileId]: !current[profileId] }));
  };

  const handleStartMission = async () => {
    if (!missionText.trim()) {
      setError('Describe the mission before starting.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const interpreted = await MissionService.getInstance().interpret(missionText.trim());
      setContract(interpreted);
      setPhase('review');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to interpret the mission.');
    } finally {
      setBusy(false);
    }
  };

  const handleConfirmContract = () => {
    setError('');
    setPhase('candidate');
  };

  const handleEvaluate = async () => {
    if (!contract) return;
    if (selectedProfileIds.length === 0) {
      setError('Select at least one candidate to evaluate.');
      return;
    }
    setBusy(true);
    setError('');
    setPhase('evaluating');
    try {
      const orderedIds = profiles
        .filter((p) => selectedProfileIds.includes(p.id))
        .map((p) => p.id);
      const evaluated = await MissionService.getInstance().evaluateMany(orderedIds, contract);
      setResults(evaluated);
      setTeamSelection({});
      setPhase('results');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to evaluate the mission.');
      setPhase('candidate');
    } finally {
      setBusy(false);
    }
  };

  const handleRestart = () => {
    setPhase('input');
    setContract(null);
    setResults([]);
    setTeamSelection({});
    setSelectedProfileIds([]);
    setMissionText('');
    setError('');
  };

  const selectedCount = Object.values(teamSelection).filter(Boolean).length;
  const teamMembers = results.filter((e) => teamSelection[e.profile_id]);

  return (
    <div className="min-h-screen bg-[#F5F9FF]">
      <header className="bg-gradient-to-r from-primary-900 via-primary-600 to-primary-500 px-6 py-10">
        <button
          onClick={() => navigate('/')}
          className="mb-4 text-sm text-blue-100 hover:text-white"
        >
          &larr; Back to Dashboard
        </button>
        <h1 className="text-3xl font-bold text-white">Mission Contract</h1>
        <p className="text-blue-100 mt-2">
          Turn a business challenge into an evidence-ready workforce mission.
        </p>
      </header>

      <main className="px-6 py-8 max-w-3xl space-y-6">
        {phase === 'input' && (
          <>
            <SectionCard title="Start a Mission">
              <label
                htmlFor="mission"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                {MISSION_PROMPT}
              </label>
              <textarea
                id="mission"
                value={missionText}
                onChange={(e) => setMissionText(e.target.value)}
                rows={5}
                placeholder="e.g. Build the right DevSecOps cloud migration team for a Nordic financial-services organization, with production AWS migration experience and GDPR/security constraints."
                className="w-full rounded-lg border border-blue-200 p-3 text-sm text-gray-800 focus:border-blue-500 focus:outline-none"
              />
              <button
                onClick={handleStartMission}
                disabled={busy}
                className="mt-6 w-full bg-gradient-to-r from-blue-600 to-blue-400 hover:from-blue-700 hover:to-blue-500 text-white font-semibold py-3 px-4 rounded-lg shadow-md shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
              >
                {busy ? 'Interpreting mission...' : 'Start Mission'}
              </button>
            </SectionCard>

            <SectionCard title="How it works">
              <ol className="space-y-3">
                {MISSION_FLOW.map((step, index) => (
                  <li key={step} className="flex items-center gap-4">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-700">
                      {index + 1}
                    </span>
                    <span className="text-sm font-medium text-gray-700">{step}</span>
                    {index < MISSION_FLOW.length - 1 && (
                      <span className="text-blue-300" aria-hidden="true">
                        &darr;
                      </span>
                    )}
                  </li>
                ))}
              </ol>
            </SectionCard>
          </>
        )}

        {phase === 'review' && contract && (
          <>
            <SectionCard title="Confirm the Mission Contract">
              <dl className="space-y-4 text-sm">
                <div>
                  <dt className="font-semibold text-gray-700">Summary</dt>
                  <dd className="text-gray-600 mt-1">{contract.summary}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-gray-700">Primary role</dt>
                  <dd className="text-gray-600 mt-1">{contract.role}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-gray-700">Requirements</dt>
                  <dd className="mt-2 flex flex-wrap gap-2">
                    {contract.requirements.map((req) => (
                      <span
                        key={req}
                        className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
                      >
                        {req}
                      </span>
                    ))}
                  </dd>
                </div>
                {contract.capabilities.length > 0 && (
                  <div>
                    <dt className="font-semibold text-gray-700">Capabilities</dt>
                    <dd className="mt-2 flex flex-wrap gap-2">
                      {contract.capabilities.map((cap) => (
                        <span
                          key={cap}
                          className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-50 text-gray-600 border border-gray-200"
                        >
                          {cap}
                        </span>
                      ))}
                    </dd>
                  </div>
                )}
                {contract.evidence_standards.length > 0 && (
                  <div>
                    <dt className="font-semibold text-gray-700">Evidence standards</dt>
                    <dd>
                      <ul className="mt-1 list-disc list-inside text-gray-600">
                        {contract.evidence_standards.map((standard) => (
                          <li key={standard}>{standard}</li>
                        ))}
                      </ul>
                    </dd>
                  </div>
                )}
                {contract.constraints.length > 0 && (
                  <div>
                    <dt className="font-semibold text-gray-700">Constraints</dt>
                    <dd>
                      <ul className="mt-1 list-disc list-inside text-gray-600">
                        {contract.constraints.map((constraint) => (
                          <li key={constraint}>{constraint}</li>
                        ))}
                      </ul>
                    </dd>
                  </div>
                )}
              </dl>
              <div className="mt-6 flex flex-col sm:flex-row gap-3">
                <button
                  onClick={handleConfirmContract}
                  disabled={busy}
                  className="flex-1 bg-gradient-to-r from-blue-600 to-blue-400 hover:from-blue-700 hover:to-blue-500 text-white font-semibold py-3 px-4 rounded-lg shadow-md shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
                >
                  Confirm Mission Contract
                </button>
                <button
                  onClick={() => setPhase('input')}
                  disabled={busy}
                  className="flex-1 bg-white border border-blue-200 text-blue-700 font-semibold py-3 px-4 rounded-lg hover:bg-blue-50 disabled:opacity-50 transition-all duration-300"
                >
                  Edit
                </button>
              </div>
            </SectionCard>
          </>
        )}

        {phase === 'candidate' && contract && (
          <>
            <SectionCard title="Choose Who to Evaluate">
              <p className="text-sm text-gray-600 mb-4">
                The mission contract is confirmed. Select one or more candidates to
                evaluate against it.
              </p>
              {profiles.length === 0 ? (
                <p className="text-sm text-gray-500">No profiles available.</p>
              ) : (
                <ul className="space-y-3">
                  {profiles.map((p) => (
                    <li key={p.id}>
                      <label className="flex items-center gap-3 rounded-lg border border-blue-200 px-4 py-3 cursor-pointer hover:bg-blue-50">
                        <input
                          type="checkbox"
                          checked={selectedProfileIds.includes(p.id)}
                          onChange={() => toggleProfile(p.id)}
                          className="h-4 w-4 rounded border-blue-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="text-sm font-medium text-gray-700">{p.name}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-4 text-sm text-gray-500">
                {selectedProfileIds.length} candidate
                {selectedProfileIds.length !== 1 ? 's' : ''} selected
              </p>
              <div className="mt-6 flex flex-col sm:flex-row gap-3">
                <button
                  onClick={handleEvaluate}
                  disabled={busy}
                  className="flex-1 bg-gradient-to-r from-blue-600 to-blue-400 hover:from-blue-700 hover:to-blue-500 text-white font-semibold py-3 px-4 rounded-lg shadow-md shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
                >
                  {busy ? 'Evaluating...' : 'Run CareerOS Evaluation'}
                </button>
                <button
                  onClick={() => setPhase('review')}
                  disabled={busy}
                  className="flex-1 bg-white border border-blue-200 text-blue-700 font-semibold py-3 px-4 rounded-lg hover:bg-blue-50 disabled:opacity-50 transition-all duration-300"
                >
                  Back to Contract
                </button>
              </div>
            </SectionCard>
          </>
        )}

        {phase === 'evaluating' && (
          <SectionCard title="Evaluating the Mission">
            <div className="flex items-center gap-3 text-gray-600">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
              Running the deterministic evidence evaluation...
            </div>
          </SectionCard>
        )}

        {phase === 'results' && (
          <>
            <SectionCard title="Candidate Results">
              <p className="text-sm text-gray-600 mb-6">
                Review the evidence-backed result for each evaluated candidate, then
                choose who you want to put forward for the mission team. Selecting a
                candidate is a human decision and does not certify them.
              </p>
              <ul className="space-y-6">
                {results.map((evaluation) => (
                  <li
                    key={evaluation.profile_id}
                    className="rounded-xl border border-blue-100 p-6"
                  >
                    <div className="flex items-center justify-between flex-wrap gap-3">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          {evaluation.result.candidate || 'Candidate'}
                        </h3>
                        <p className="text-sm text-gray-500 mt-1">
                          {evaluation.result.mission_statement}
                        </p>
                      </div>
                      <span
                        className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${STATUS_STYLES[evaluation.result.status]}`}
                      >
                        {STATUS_LABELS[evaluation.result.status]}
                      </span>
                    </div>
                    <label className="mt-4 flex items-center gap-3 rounded-lg border border-blue-200 px-4 py-3 cursor-pointer hover:bg-blue-50">
                      <input
                        type="checkbox"
                        checked={teamSelection[evaluation.profile_id] ?? false}
                        onChange={() => toggleTeamSelection(evaluation.profile_id)}
                        className="h-4 w-4 rounded border-blue-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm font-semibold text-blue-700">
                        Select for Mission Team
                      </span>
                    </label>
                    <ResultDetail result={evaluation.result} />
                  </li>
                ))}
              </ul>
              <div className="mt-6 flex flex-col sm:flex-row gap-3">
                <button
                  onClick={() => setPhase('team')}
                  disabled={selectedCount === 0}
                  className="flex-1 bg-gradient-to-r from-blue-600 to-blue-400 hover:from-blue-700 hover:to-blue-500 text-white font-semibold py-3 px-4 rounded-lg shadow-md shadow-blue-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
                >
                  Review Proposed Mission Team ({selectedCount})
                </button>
                <button
                  onClick={() => setPhase('candidate')}
                  disabled={busy}
                  className="flex-1 bg-white border border-blue-200 text-blue-700 font-semibold py-3 px-4 rounded-lg hover:bg-blue-50 disabled:opacity-50 transition-all duration-300"
                >
                  Back to Choose Candidates
                </button>
              </div>
            </SectionCard>
          </>
        )}

        {phase === 'team' && (
          <>
            <SectionCard title="Proposed Mission Team">
              <p className="text-sm text-gray-600 mb-6">
                {teamMembers.length} person
                {teamMembers.length !== 1 ? 's' : ''} selected for the mission team.
                CareerOS evaluated each person individually against the mission
                contract; these are the people you are putting forward.
              </p>
              <ul className="space-y-6">
                {teamMembers.map((evaluation) => (
                  <li key={evaluation.profile_id} className="rounded-xl border border-blue-100 p-6">
                    <div className="flex items-center justify-between flex-wrap gap-3">
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900">
                          {evaluation.result.candidate || 'Candidate'}
                        </h3>
                        <p className="text-sm text-gray-500 mt-1">
                          {evaluation.result.mission_statement}
                        </p>
                      </div>
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">
                        Selected for mission team
                      </span>
                    </div>
                    <ResultDetail result={evaluation.result} />
                  </li>
                ))}
              </ul>
              <p className="mt-6 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm p-4">
                {TEAM_NOTE}
              </p>
              <div className="mt-6 flex flex-col sm:flex-row gap-3">
                <button
                  onClick={handleRestart}
                  className="flex-1 bg-gradient-to-r from-blue-600 to-blue-400 hover:from-blue-700 hover:to-blue-500 text-white font-semibold py-3 px-4 rounded-lg shadow-md shadow-blue-600/20 transition-all duration-300"
                >
                  Start a New Mission
                </button>
                <button
                  onClick={() => setPhase('results')}
                  className="flex-1 bg-white border border-blue-200 text-blue-700 font-semibold py-3 px-4 rounded-lg hover:bg-blue-50 transition-all duration-300"
                >
                  Back to Candidate Results
                </button>
              </div>
            </SectionCard>
          </>
        )}

        {error && (
          <p className="rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm p-4">
            {error}
          </p>
        )}
      </main>
    </div>
  );
}
