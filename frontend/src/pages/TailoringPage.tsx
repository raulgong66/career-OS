import { useState, useEffect } from 'react';
import { TailoringService } from '../services/TailoringService';
import { DocumentService } from '../services/DocumentService';
import { ProfileService } from '../services/ProfileService';
import type {
  Recommendation,
  OptimizationStatus,
  OptimizationSummary,
  ProfileInfo,
  ProfileDetails,
  ProfileRecommendation,
  RecommendationConfidence,
} from '../types';

type RequestStatus = 'idle' | 'analyzing' | 'generating' | 'success' | 'error';

interface ArtifactLabels {
  resultHeading: string;
  emptyState: string;
  completeMessage: string;
}

const CONFIDENCE_STYLES: Record<RecommendationConfidence, string> = {
  high: 'bg-green-100 text-green-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-gray-100 text-gray-700',
};

const ARTIFACT_LABELS: Record<string, ArtifactLabels> = {
  CV: {
    resultHeading: 'Tailored CV',
    emptyState: 'Your tailored CV will appear here',
    completeMessage: 'CV is already complete',
  },
  INTEREST_LETTER: {
    resultHeading: 'Interest Letter',
    emptyState: 'Your interest letter will appear here',
    completeMessage: 'Interest letter is already complete',
  },
};

const TEMPLATE_IDS: Record<string, string> = {
  CV: 'standard_cv',
  INTEREST_LETTER: 'standard_interest_letter',
};

const DEFAULT_LABELS: ArtifactLabels = {
  resultHeading: 'Tailored Document',
  emptyState: 'Your tailored document will appear here',
  completeMessage: 'Document is already complete',
};

function getArtifactLabels(artifactType: string): ArtifactLabels {
  if (artifactType in ARTIFACT_LABELS) return ARTIFACT_LABELS[artifactType];
  return DEFAULT_LABELS;
}

export default function TailoringPage() {
  const [profiles, setProfiles] = useState<ProfileInfo[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [selectedProfile, setSelectedProfile] = useState<ProfileDetails | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [status, setStatus] = useState<RequestStatus>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [artifact, setArtifact] = useState<string>('');
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [optimizationStatus, setOptimizationStatus] = useState<OptimizationStatus | null>(null);
  const [optimizationMessage, setOptimizationMessage] = useState('');
  const [optimizationSummary, setOptimizationSummary] = useState<OptimizationSummary | null>(null);
  const [currentArtifactId, setCurrentArtifactId] = useState('');
  const [currentArtifactType, setCurrentArtifactType] = useState('');
  const [profileRecommendations, setProfileRecommendations] = useState<ProfileRecommendation[]>([]);
  const [recommendationsLoading, setRecommendationsLoading] = useState(false);
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const labels = getArtifactLabels(currentArtifactType);

  const loadProfileRecommendations = (profileId: string) => {
    setProfileRecommendations([]);
    setRecommendationsLoading(true);
    ProfileService.getInstance().analyzeProfile(profileId)
      .then((result) => {
        setProfileRecommendations(result.recommendations ?? []);
      })
      .catch(() => {
        setProfileRecommendations([]);
      })
      .finally(() => {
        setRecommendationsLoading(false);
      });
  };

  useEffect(() => {
    setLoadingProfiles(true);
    const service = TailoringService.getInstance();
    service.getProfiles().then((profiles) => {
      setProfiles(profiles);
      if (profiles.length > 0) {
        setSelectedProfileId(profiles[0].id);
        loadProfileRecommendations(profiles[0].id);
        ProfileService.getInstance().getProfile(profiles[0].id).then((details) => {
          setSelectedProfile(details);
        }).catch(() => {}).finally(() => setLoadingProfiles(false));
      } else {
        setLoadingProfiles(false);
      }
    }).catch(() => {
      setErrorMessage('Unable to load profiles. Please ensure the backend is running.');
      setLoadingProfiles(false);
    });
  }, []);

  const handleProfileChange = (profileId: string) => {
    setSelectedProfileId(profileId);
    setSelectedProfile(null);
    loadProfileRecommendations(profileId);
    ProfileService.getInstance().getProfile(profileId).then((details) => {
      setSelectedProfile(details);
      setErrorMessage('');
    }).catch(() => {
      setErrorMessage('Failed to load profile details. Please try again.');
    });
  };

  const generateDocument = async (artifactType: 'CV' | 'INTEREST_LETTER') => {
    if (!jobDescription.trim()) {
      setErrorMessage('Please enter a job description');
      setStatus('error');
      return;
    }

    setErrorMessage('');
    setStatus('analyzing');

    try {
      setArtifact('');
      setRecommendations([]);
      setOptimizationStatus(null);
      setOptimizationMessage('');
      setOptimizationSummary(null);

      let artifactId: string | null = null;
      const existing = selectedProfile?.artifacts.find((a: { type: string }) => a.type === artifactType);
      if (existing) {
        artifactId = existing.id;
      } else {
        const result = await ProfileService.getInstance().createArtifact(selectedProfileId, TEMPLATE_IDS[artifactType]);
        const details = await ProfileService.getInstance().getProfile(selectedProfileId);
        setSelectedProfile(details);
        artifactId = result.artifactId;
      }

      setCurrentArtifactId(artifactId);
      setCurrentArtifactType(artifactType);

      const generatingTimeout = setTimeout(() => {
        setStatus('generating');
      }, 800);

      const service = TailoringService.getInstance();
      const response = await service.generateTailoredArtifact(
        selectedProfileId,
        artifactId,
        'markdown',
        jobDescription
      );

      clearTimeout(generatingTimeout);

      setArtifact(response.artifact);
      setRecommendations(response.recommendations);
      setOptimizationStatus(response.optimizationStatus);
      setOptimizationMessage(response.optimizationMessage);
      setOptimizationSummary(response.optimizationSummary);
      setStatus('success');
    } catch (error) {
      setStatus('error');
      setErrorMessage(
        error instanceof Error && error.message.includes('Failed to fetch')
          ? 'Unable to connect to the server. Please ensure the backend is running.'
          : error instanceof Error
          ? error.message
          : 'Failed to generate document'
      );
    }
  };

  const formatDateRange = (dr: import('../types').DateRange | null): string => {
    if (!dr) return '';
    if (dr.label) return dr.label;
    const parts: string[] = [];
    if (dr.start) parts.push(dr.start);
    if (dr.isCurrent) {
      parts.push('Present');
    } else if (dr.end) {
      parts.push(dr.end);
    }
    return parts.join(' – ');
  };

  const renderEntitySections = (profile: import('../types').ProfileDetails) => (
    <div className="space-y-4">
      {/* Professional Summary */}
      {profile.professionalSummaries.length > 0 && (
        <div className="border border-gray-200 rounded-md divide-y divide-gray-200">
          <div className="px-3 py-2 bg-gray-50">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Professional Summary</h3>
          </div>
          {profile.professionalSummaries.map((ps) => (
            <div key={ps.id} className="px-3 py-2">
              {ps.label && <p className="text-xs font-medium text-gray-500 mb-1">{ps.label}</p>}
              <p className="text-sm text-gray-700 leading-relaxed">{ps.text}</p>
            </div>
          ))}
        </div>
      )}

      {/* Experience */}
      <div className="border border-gray-200 rounded-md divide-y divide-gray-200">
        <div className="px-3 py-2 bg-gray-50">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Experience</h3>
        </div>
        {profile.experiences.length === 0 ? (
          <div className="px-3 py-4">
            <p className="text-sm text-gray-400 italic">No experience entries available.</p>
          </div>
        ) : (
          profile.experiences.map((exp) => (
            <div key={exp.id} className="px-3 py-2">
              <p className="text-sm font-medium text-gray-900">{exp.title}</p>
              {(exp.organization || exp.engagementType) && (
                <p className="text-xs text-gray-500 mt-0.5">
                  {[exp.organization, exp.engagementType].filter(Boolean).join(' · ')}
                </p>
              )}
              {formatDateRange(exp.dateRange) && (
                <p className="text-xs text-gray-400 mt-0.5">{formatDateRange(exp.dateRange)}</p>
              )}
              {exp.scope && (
                <p className="text-sm text-gray-700 mt-1 leading-relaxed">{exp.scope}</p>
              )}
            </div>
          ))
        )}
      </div>

      {/* Skills */}
      <div className="border border-gray-200 rounded-md divide-y divide-gray-200">
        <div className="px-3 py-2 bg-gray-50">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Skills</h3>
        </div>
        {profile.skills.length === 0 ? (
          <div className="px-3 py-4">
            <p className="text-sm text-gray-400 italic">No skills available.</p>
          </div>
        ) : (
          <div className="px-3 py-2">
            <div className="flex flex-wrap gap-1.5">
              {profile.skills.map((skill) => (
                <span
                  key={skill.id}
                  className="inline-flex items-center px-2.5 py-1 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
                  title={skill.description || skill.category || undefined}
                >
                  {skill.name}
                  {skill.proficiency && (
                    <span className="ml-1 text-blue-400 font-normal">({skill.proficiency})</span>
                  )}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Education */}
      <div className="border border-gray-200 rounded-md divide-y divide-gray-200">
        <div className="px-3 py-2 bg-gray-50">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Education</h3>
        </div>
        {profile.education.length === 0 ? (
          <div className="px-3 py-4">
            <p className="text-sm text-gray-400 italic">No education entries available.</p>
          </div>
        ) : (
          profile.education.map((edu) => (
            <div key={edu.id} className="px-3 py-2">
              <p className="text-sm font-medium text-gray-900">{edu.program}</p>
              {(edu.institution || edu.fieldOfStudy) && (
                <p className="text-xs text-gray-500 mt-0.5">
                  {[edu.institution, edu.fieldOfStudy].filter(Boolean).join(' · ')}
                </p>
              )}
              {formatDateRange(edu.dateRange) && (
                <p className="text-xs text-gray-400 mt-0.5">{formatDateRange(edu.dateRange)}</p>
              )}
            </div>
          ))
        )}
      </div>

      {/* Certifications */}
      <div className="border border-gray-200 rounded-md divide-y divide-gray-200">
        <div className="px-3 py-2 bg-gray-50">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Certifications</h3>
        </div>
        {profile.certifications.length === 0 ? (
          <div className="px-3 py-4">
            <p className="text-sm text-gray-400 italic">No certifications available.</p>
          </div>
        ) : (
          profile.certifications.map((cert) => (
            <div key={cert.id} className="px-3 py-2">
              <p className="text-sm font-medium text-gray-900">{cert.name}</p>
              {cert.issuer && (
                <p className="text-xs text-gray-500 mt-0.5">{cert.issuer}</p>
              )}
              {formatDateRange(cert.dateRange) && (
                <p className="text-xs text-gray-400 mt-0.5">{formatDateRange(cert.dateRange)}</p>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );

  const renderResume = (content: string) => {
    const lines = content.split('\n');
    return lines.map((line, index) => {
      if (line.startsWith('# ')) {
        return <h3 key={index} className="text-lg font-bold text-gray-900 mt-4 mb-2">{line.slice(2)}</h3>;
      }
      if (line.startsWith('## ')) {
        return <h4 key={index} className="text-base font-semibold text-gray-900 mt-3 mb-1">{line.slice(3)}</h4>;
      }
      if (line.startsWith('- ')) {
        return <li key={index} className="text-sm text-gray-700 ml-4">{line.slice(2)}</li>;
      }
      if (line.trim()) {
        return <p key={index} className="text-sm text-gray-700 mb-1">{line}</p>;
      }
      return <br key={index} />;
    });
  };

  const getRecommendationReason = (rec: Recommendation): string | null => {
    if (rec.evidence && rec.evidence.length > 0) {
      const evidence = rec.evidence[0];
      if (typeof evidence === 'object' && evidence !== null) {
        const reason = (evidence as any).reason || (evidence as any).description;
        if (reason) return reason;
      }
    }
    if (rec.details && typeof rec.details === 'object') {
      const reason = (rec.details as any).reason;
      if (reason) return reason;
    }
    return null;
  };

  const getRecommendationImpact = (rec: Recommendation): string | null => {
    if (rec.details && typeof rec.details === 'object') {
      const impact = (rec.details as any).impact;
      if (impact) return impact;
    }
    return null;
  };

  const getRecommendationConfidence = (rec: Recommendation): number | null => {
    if (rec.scores && Object.keys(rec.scores).length > 0) {
      const scoreValue = Object.values(rec.scores)[0];
      if (typeof scoreValue === 'number') {
        return Math.round(scoreValue * 100);
      }
    }
    return null;
  };

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">CareerOS Platform Alpha</h1>
        <p className="text-sm text-gray-600 mt-1">AI-Powered Document Tailoring</p>
      </header>

      <div className="flex-1 overflow-hidden">
        <div className="h-full grid grid-cols-1 lg:grid-cols-2">
          {/* Left Panel */}
          <div className="border-r border-gray-200 bg-white p-6 overflow-y-auto">
            {loadingProfiles ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <svg className="animate-spin h-8 w-8 mb-3 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <p className="text-sm">Loading profiles...</p>
              </div>
            ) : (
            <div className="max-w-xl mx-auto space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Source Profile</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Profile</label>
                    <select
                      value={selectedProfileId}
                      onChange={(e) => handleProfileChange(e.target.value)}
                      className="w-full p-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {profiles.length === 0 && <option value="">Loading profiles...</option>}
                      {profiles.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>
                  {selectedProfile && (
                    <>
                      <div className="border border-gray-200 rounded-md divide-y divide-gray-200">
                        <div className="px-3 py-2">
                          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Name</label>
                          <p className="mt-0.5 text-sm text-gray-900">{selectedProfile.person.firstName} {selectedProfile.person.lastName}</p>
                        </div>
                        <div className="px-3 py-2">
                          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Headline</label>
                          <p className="mt-0.5 text-sm text-gray-700">{selectedProfile.person.headline || '—'}</p>
                        </div>
                        <div className="px-3 py-2">
                          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Location</label>
                          <p className="mt-0.5 text-sm text-gray-700">
                            {[selectedProfile.person.city, selectedProfile.person.country].filter(Boolean).join(', ') || '—'}
                          </p>
                        </div>
                        <div className="px-3 py-2">
                          <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Languages</label>
                          <p className="mt-0.5 text-sm text-gray-700">
                            {selectedProfile.person.languages.length > 0
                              ? selectedProfile.person.languages.map((l) => `${l.name} (${l.proficiency})`).join(', ')
                              : '—'}
                          </p>
                        </div>
                        {selectedProfile.summary && (
                          <div className="px-3 py-2">
                            <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Summary</label>
                            <p className="mt-0.5 text-sm text-gray-700 leading-relaxed">{selectedProfile.summary}</p>
                          </div>
                        )}
                      </div>

                      {/* ── Entity Sections ── */}
                      {renderEntitySections(selectedProfile)}
                    </>
                  )}
                  </div>
                </div>

              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Paste Job Description</h2>
                <textarea
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Paste the job description here..."
                  className="w-full h-48 p-3 border border-gray-300 rounded-md text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex gap-3">
                {(['CV', 'INTEREST_LETTER'] as const).map((type) => {
                  const isActive = status === 'analyzing' || status === 'generating';
                  const label = type === 'CV' ? 'Generate Tailored CV' : 'Generate Interest Letter';
                  return (
                    <button
                      key={type}
                      onClick={() => generateDocument(type)}
                      disabled={isActive || !jobDescription.trim() || !selectedProfile}
                      className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-md transition-colors duration-200"
                    >
                      {isActive ? (
                        <span className="flex items-center justify-center">
                          <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          {status === 'analyzing' ? 'Analyzing' : 'Generating...'}
                        </span>
                      ) : (
                        label
                      )}
                    </button>
                  );
                })}
              </div>

              {status === 'error' && (
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                  <p className="text-sm text-red-700">{errorMessage}</p>
                </div>
              )}
            </div>
            )}
          </div>

          {/* Right Panel */}
          <div className="bg-gray-50 p-6 overflow-y-auto">
            <div className="max-w-2xl mx-auto space-y-6">

              {/* ── Status Banner ── */}
                    {status === 'success' && optimizationStatus === 'already_complete' && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-5">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-0.5">
                      <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-base font-semibold text-green-800">Optimization Complete</h2>
                      <p className="mt-1 text-sm text-green-700 leading-relaxed">
                        Your profile already contains all verified evidence relevant to this opportunity.
                        No additional profile information needs to be incorporated.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {status === 'success' && optimizationStatus === 'no_matches' && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-5">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-0.5">
                      <svg className="h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-base font-semibold text-blue-800">Analysis Complete</h2>
                      <p className="mt-1 text-sm text-blue-700 leading-relaxed">{optimizationMessage}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* ── Metric Cards ── */}
              {status === 'success' && optimizationSummary && (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Profile Coverage</span>
                      <svg className="h-4 w-4 text-green-400" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z" />
                      </svg>
                    </div>
                    <p className="text-3xl font-bold text-green-600">{optimizationSummary.profile_coverage.toFixed(0)}<span className="text-lg font-semibold">%</span></p>
                    <p className="mt-1.5 text-xs text-gray-500">All profile evidence included</p>
                  </div>

                  <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Job Match</span>
                      <svg className="h-4 w-4 text-blue-400" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
                      </svg>
                    </div>
                    <p className="text-3xl font-bold text-blue-600">{optimizationSummary.requirement_coverage?.toFixed(0) ?? '—'}<span className="text-lg font-semibold">%</span></p>
                    <p className="mt-1.5 text-xs text-gray-500">Requirements satisfied</p>
                  </div>

                  <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Job Requirements</span>
                      <svg className="h-4 w-4 text-purple-400" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                      </svg>
                    </div>
                    <p className="text-3xl font-bold text-purple-600">{optimizationSummary.requirements_detected ?? '—'}</p>
                    <p className="mt-1.5 text-xs text-gray-500">Requirements identified</p>
                  </div>

                  <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Matching Competencies</span>
                      <svg className="h-4 w-4 text-orange-400" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
                      </svg>
                    </div>
                    <p className="text-3xl font-bold text-orange-600">{optimizationSummary.matched_requirements.length}</p>
                    <p className="mt-1.5 text-xs text-gray-500">Relevant competencies found</p>
                  </div>
                </div>
              )}

              {/* ── Analysis Explanation ── */}
              {status === 'success' && optimizationSummary && (
                <p className="text-sm text-gray-500 leading-relaxed border-l-2 border-gray-200 pl-4">
                  The AI analyzed the job description, compared it with your professional profile,
                  and generated this tailored document using verified profile evidence.
                </p>
              )}

              {/* ── Job Match Analysis ── */}
              {status === 'success' && optimizationSummary && (optimizationSummary.matched_requirements.length > 0 || optimizationSummary.target_context_emphasis.length > 0) && (
                <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                  <h2 className="text-base font-semibold text-gray-900 mb-4">Job Match Analysis</h2>

                  {optimizationSummary.matched_requirements.length > 0 && (
                    <div className="mb-5">
                      <h3 className="text-sm font-medium text-gray-700 mb-2.5">Matching Competencies</h3>
                      <div className="flex flex-wrap gap-2">
                        {optimizationSummary.matched_requirements.map((req) => (
                          <span key={req} className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                            {req}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {optimizationSummary.target_context_emphasis.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-gray-700 mb-2.5">Target Context</h3>
                      <div className="flex flex-wrap gap-2">
                        {optimizationSummary.target_context_emphasis.map((emphasis) => (
                          <span key={emphasis} className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
                            {emphasis}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── Generated Artifact ── */}
              <div>
                <h2 className="text-base font-semibold text-gray-900 mb-3">{labels.resultHeading}</h2>
                {artifact ? (
                  <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                    <div className="flex items-center justify-end gap-2 mb-4 pb-3 border-b border-gray-100">
                      <button
                        onClick={async () => {
                          try {
                            const docService = DocumentService.getInstance();
                            const blob = await docService.downloadDocx(selectedProfileId, currentArtifactId);
                            const ext = currentArtifactType ? `${currentArtifactType.replace(/_/g, '-')}.docx` : 'document.docx';
                            docService.downloadBlob(blob, ext);
                          } catch (err) {
                            setErrorMessage(err instanceof Error ? err.message : 'Download failed');
                          }
                        }}
                        className="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 transition-colors"
                      >
                        Download DOCX
                      </button>
                    </div>
                    <div className="prose prose-sm max-w-none">
                      {renderResume(artifact)}
                    </div>
                  </div>
                ) : (
                  <div className="bg-white border border-gray-200 rounded-lg p-12 shadow-sm flex flex-col items-center justify-center text-gray-400">
                    <svg className="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    <p className="text-sm">{labels.emptyState}</p>
                  </div>
                )}
              </div>

              {/* ── Recommendations ── */}
              <div>
                <h2 className="text-base font-semibold text-gray-900 mb-3">
                  Recommendations{' '}
                  {(profileRecommendations.length > 0 || recommendations.length > 0) && `(${profileRecommendations.length + recommendations.length})`}
                </h2>
                {profileRecommendations.length > 0 || recommendations.length > 0 ? (
                  <div className="space-y-6">
                    {profileRecommendations.length > 0 && (
                      <div className="space-y-3">
                        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                          Profile Recommendations ({profileRecommendations.length})
                        </h3>
                        {profileRecommendations.map((rec) => (
                          <div key={rec.id} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                            <div className="flex items-start justify-between gap-3">
                              <h4 className="font-semibold text-gray-900">{rec.title}</h4>
                              <span className={`inline-flex items-center shrink-0 px-2 py-1 rounded text-xs font-medium ${CONFIDENCE_STYLES[rec.confidence] ?? 'bg-gray-100 text-gray-700'}`}>
                                {rec.confidence} confidence
                              </span>
                            </div>
                            <p className="mt-2 text-sm text-gray-700 leading-relaxed">{rec.reason}</p>
                          </div>
                        ))}
                      </div>
                    )}

                    {recommendations.length > 0 && (
                      <div className="space-y-3">
                        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                          Optimization Recommendations ({recommendations.length})
                        </h3>
                        {recommendations.map((rec) => (
                          <div key={rec.id} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                            <div className="flex items-start justify-between">
                              <h4 className="font-semibold text-gray-900">{rec.displayName}</h4>
                              {getRecommendationConfidence(rec) !== null && (
                                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                                  {getRecommendationConfidence(rec)}% match
                                </span>
                              )}
                            </div>
                            <div className="mt-2 text-sm text-gray-600">
                              <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 mr-2">
                                {rec.type}
                              </span>
                              <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                                {rec.operation}
                              </span>
                            </div>
                            {getRecommendationReason(rec) && (
                              <p className="mt-2 text-sm text-gray-700">{getRecommendationReason(rec)}</p>
                            )}
                            {getRecommendationImpact(rec) && (
                              <p className="mt-1 text-sm text-gray-600 italic">{getRecommendationImpact(rec)}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-white border border-gray-200 rounded-lg p-12 shadow-sm flex flex-col items-center justify-center text-gray-400">
                    <svg className="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                    </svg>
                    <p className="text-sm">
                      {recommendationsLoading ? 'Analyzing profile recommendations...' :
                       status === 'analyzing' || status === 'generating' ? 'Analyzing recommendations...' :
                       status === 'success' && optimizationStatus === 'already_complete' ? labels.completeMessage :
                       status === 'success' && optimizationStatus === 'no_matches' ? 'No additional evidence found' :
                       'No recommendations — your profile looks strong'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
