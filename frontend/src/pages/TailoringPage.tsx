import { useState } from 'react';
import { TailoringService } from '../services/TailoringService';
import type { Recommendation, OptimizationStatus } from '../types';

type RequestStatus = 'idle' | 'analyzing' | 'generating' | 'success' | 'error';

export default function TailoringPage() {
  const [profilePath, setProfilePath] = useState('C:\\Users\\raul\\AI\\careeros\\career-OS\\profiles\\raul-gongora-profile.yaml');
  const [artifactId, setArtifactId] = useState('cv-english-source');
  const [jobDescription, setJobDescription] = useState('');
  const [status, setStatus] = useState<RequestStatus>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [artifact, setArtifact] = useState<string>('');
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [optimizationStatus, setOptimizationStatus] = useState<OptimizationStatus | null>(null);
  const [optimizationMessage, setOptimizationMessage] = useState('');

  const handleGenerate = async () => {
    if (!jobDescription.trim()) {
      setErrorMessage('Please enter a job description');
      setStatus('error');
      return;
    }

    setStatus('analyzing');
    setErrorMessage('');
    setArtifact('');
    setRecommendations([]);
    setOptimizationStatus(null);
    setOptimizationMessage('');

    const generatingTimeout = setTimeout(() => {
      setStatus('generating');
    }, 800);

    try {
      const service = TailoringService.getInstance();

      const response = await service.generateTailoredArtifact(
        profilePath,
        artifactId,
        'markdown',
        jobDescription
      );

      clearTimeout(generatingTimeout);
      setArtifact(response.artifact);
      setRecommendations(response.recommendations);
      setOptimizationStatus(response.optimizationStatus);
      setOptimizationMessage(response.optimizationMessage);
      setStatus('success');
    } catch (error) {
      clearTimeout(generatingTimeout);
      setErrorMessage(
        error instanceof Error && error.message.includes('Failed to fetch')
          ? 'Unable to connect to the server. Please ensure the backend is running.'
          : error instanceof Error
          ? error.message
          : 'Failed to generate tailored resume'
      );
      setStatus('error');
    }
  };

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
        <p className="text-sm text-gray-600 mt-1">AI-Powered Resume Tailoring</p>
      </header>

      <div className="flex-1 overflow-hidden">
        <div className="h-full grid grid-cols-1 lg:grid-cols-2">
          {/* Left Panel */}
          <div className="border-r border-gray-200 bg-white p-6 overflow-y-auto">
            <div className="max-w-xl mx-auto space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Resume</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Profile Path</label>
                    <input
                      type="text"
                      value={profilePath}
                      onChange={(e) => setProfilePath(e.target.value)}
                      className="w-full p-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Artifact ID</label>
                    <input
                      type="text"
                      value={artifactId}
                      onChange={(e) => setArtifactId(e.target.value)}
                      className="w-full p-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
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

              <button
                onClick={handleGenerate}
                disabled={status === 'analyzing' || status === 'generating' || !jobDescription.trim()}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-md transition-colors duration-200"
              >
                {status === 'analyzing' || status === 'generating' ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {status === 'analyzing' ? 'Analyzing job description...' : 'Generating tailored resume...'}
                  </span>
                ) : 'Generate Tailored Resume'}
              </button>

              {status === 'error' && (
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                  <p className="text-sm text-red-700">{errorMessage}</p>
                </div>
              )}

              {status === 'success' && optimizationStatus === 'already_complete' && (
                <div className="bg-green-50 border border-green-200 rounded-md p-4">
                  <p className="text-sm text-green-700">{optimizationMessage}</p>
                </div>
              )}

              {status === 'success' && optimizationStatus === 'no_matches' && (
                <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                  <p className="text-sm text-blue-700">{optimizationMessage}</p>
                </div>
              )}
            </div>
          </div>

          {/* Right Panel */}
          <div className="bg-gray-50 p-6 overflow-y-auto">
            <div className="max-w-2xl mx-auto space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Tailored Resume</h2>
                {artifact ? (
                  <div className="bg-white border border-gray-200 rounded-md p-6 shadow-sm">
                    <div className="prose prose-sm max-w-none">
                      {renderResume(artifact)}
                    </div>
                  </div>
                ) : (
                  <div className="bg-white border border-gray-200 rounded-md p-12 shadow-sm flex flex-col items-center justify-center text-gray-400">
                    <svg className="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    <p className="text-sm">Your tailored resume will appear here</p>
                  </div>
                )}
              </div>

              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  AI Recommendations {recommendations.length > 0 && `(${recommendations.length})`}
                </h2>
                {recommendations.length > 0 ? (
                  <div className="space-y-3">
                    {recommendations.map((rec) => (
                      <div key={rec.id} className="bg-white border border-gray-200 rounded-md p-4 shadow-sm">
                        <div className="flex items-start justify-between">
                          <h3 className="font-semibold text-gray-900">{rec.displayName}</h3>
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
                ) : (
                  <div className="bg-white border border-gray-200 rounded-md p-12 shadow-sm flex flex-col items-center justify-center text-gray-400">
                    <svg className="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                    </svg>
                    <p className="text-sm">
                      {status === 'analyzing' || status === 'generating' ? 'Analyzing recommendations...' :
                       status === 'success' && optimizationStatus === 'already_complete' ? 'Resume is already complete' :
                       status === 'success' && optimizationStatus === 'no_matches' ? 'No additional evidence found' :
                       'AI recommendations will appear here'}
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
