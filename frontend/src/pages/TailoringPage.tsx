import { useState } from 'react';
import { TailoringService } from '../services/TailoringService';
import type { Recommendation } from '../types';

type RequestStatus = 'idle' | 'loading' | 'success' | 'error';

export default function TailoringPage() {
  const [profilePath, setProfilePath] = useState('/Users/admin/Documents/Codex/2026-07-17/clone-my-github-repository-https-github/career-OS/profiles/raul-gongora-profile.yaml');
  const [artifactId, setArtifactId] = useState('cv-1');
  const [jobDescription, setJobDescription] = useState('');
  const [status, setStatus] = useState<RequestStatus>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [artifact, setArtifact] = useState<string>('');
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

  const handleGenerate = async () => {
    if (!jobDescription.trim()) {
      setErrorMessage('Please enter a job description');
      setStatus('error');
      return;
    }

    setStatus('loading');
    setErrorMessage('');
    setArtifact('');
    setRecommendations([]);

    try {
      const service = TailoringService.getInstance();
      const response = await service.generateTailoredArtifact(
        profilePath,
        artifactId,
        'markdown',
        jobDescription
      );

      setArtifact(response.artifact);
      setRecommendations(response.recommendations);
      setStatus('success');

      if (response.recommendations.length === 0) {
        setErrorMessage('No recommendations generated');
      }
    } catch (error) {
      console.error('Error generating tailored artifact:', error);
      setErrorMessage(error instanceof Error ? error.message : 'Failed to generate tailored resume');
      setStatus('error');
    }
  };

  return (
    <div className="min-h-screen bg-white px-4 py-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-900 mb-8">
          Resume Tailoring
        </h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column */}
          <div className="space-y-6">
            {/* Profile Input */}
            <div className="bg-gray-50 rounded-xl p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Profile
              </h2>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Profile Path
                </label>
                <input
                  type="text"
                  value={profilePath}
                  onChange={(e) => setProfilePath(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Enter profile path"
                />
              </div>
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Artifact ID
                </label>
                <input
                  type="text"
                  value={artifactId}
                  onChange={(e) => setArtifactId(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Enter artifact ID"
                />
              </div>
            </div>

            {/* Job Description */}
            <div className="bg-gray-50 rounded-xl p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Job Description
              </h2>
              <textarea
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste job description here..."
                className="w-full h-64 p-4 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            {/* Generate Button */}
            <button
              onClick={handleGenerate}
              disabled={status === 'loading' || !jobDescription.trim()}
              className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-xl font-semibold py-4 px-8 rounded-lg transition-colors duration-200"
            >
              {status === 'loading' ? 'Generating...' : 'Generate Tailored Resume'}
            </button>

            {/* Status */}
            {status !== 'idle' && (
              <div className={`p-4 rounded-lg ${
                status === 'loading' ? 'bg-blue-50 text-blue-700' :
                status === 'success' ? 'bg-green-50 text-green-700' :
                'bg-red-50 text-red-700'
              }`}>
                <div className="font-semibold">
                  {status === 'loading' && 'Processing...'}
                  {status === 'success' && 'Success'}
                  {status === 'error' && 'Error'}
                </div>
                {errorMessage && <div className="text-sm mt-1">{errorMessage}</div>}
              </div>
            )}
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Generated Resume */}
            <div className="bg-gray-50 rounded-xl p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Generated Resume
              </h2>
              {artifact ? (
                <div className="bg-white border border-gray-200 rounded-lg p-4 h-96 overflow-y-auto">
                  <pre className="whitespace-pre-wrap text-sm text-gray-700">
                    {artifact}
                  </pre>
                </div>
              ) : (
                <div className="bg-white border border-gray-200 rounded-lg p-8 h-96 flex items-center justify-center text-gray-400">
                  Generated resume will appear here
                </div>
              )}
            </div>

            {/* Recommendations */}
            <div className="bg-gray-50 rounded-xl p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Recommendations ({recommendations.length})
              </h2>
              {recommendations.length > 0 ? (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {recommendations.map((rec) => (
                    <div key={rec.id} className="bg-white border border-gray-200 rounded-lg p-4">
                      <div className="font-semibold text-gray-900 mb-2">
                        {rec.displayName}
                      </div>
                      <div className="text-sm text-gray-600 mb-2">
                        Type: {rec.type} • Operation: {rec.operation}
                      </div>
                      {rec.scores && Object.keys(rec.scores).length > 0 && (
                        <div className="text-sm text-gray-600">
                          Confidence: {Object.values(rec.scores)[0]?.toFixed(2) || 'N/A'}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="bg-white border border-gray-200 rounded-lg p-8 text-gray-400">
                  {status === 'loading' ? 'Loading recommendations...' :
                   status === 'success' ? 'No recommendations available' :
                   'Recommendations will appear here'}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
