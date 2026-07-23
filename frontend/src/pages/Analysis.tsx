import { useNavigate, useLocation } from 'react-router-dom';
import type { AnalysisResult, Profile } from '../types';

export default function Analysis() {
  const navigate = useNavigate();
  const location = useLocation();
  const { result, profile } = location.state as { result: AnalysisResult; profile: Profile };

  const handleContinue = () => {
    navigate('/preview', { state: { profile } });
  };

  return (
    <div className="min-h-screen bg-white px-4 py-12">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-900 mb-8">
          Analysis
        </h1>

        <div className="space-y-6">
          <div className="bg-gray-50 rounded-xl p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Match Score
            </h2>
            <div className="text-5xl font-bold text-primary-600">
              {result.matchScore}%
            </div>
          </div>

          <div className="bg-gray-50 rounded-xl p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Strengths
            </h2>
            <div className="space-y-2">
              {result.strengths.map((strength, index) => (
                <div key={index} className="bg-success-50 text-success-700 px-4 py-2 rounded-lg">
                  {strength}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gray-50 rounded-xl p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Missing Skills
            </h2>
            <div className="space-y-2">
              {result.missingSkills.map((skill, index) => (
                <div key={index} className="bg-warning-50 text-warning-700 px-4 py-2 rounded-lg">
                  {skill}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gray-50 rounded-xl p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Recommendations
            </h2>
            <div className="space-y-3">
              {result.recommendations.map((rec) => (
                <div key={rec.id} className="bg-white border border-gray-200 rounded-lg p-4">
                  <div className="font-semibold text-gray-900 mb-2">
                    {rec.displayName}
                  </div>
                  <div className="text-sm text-gray-600">
                    Type: {rec.type} • Operation: {rec.operation}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gray-50 rounded-xl p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Processing Timeline
            </h2>
            <div className="space-y-3">
              {result.timeline.map((step) => (
                <div key={step.id} className="flex items-center space-x-3">
                  <div className={`w-3 h-3 rounded-full ${
                    step.status === 'completed' ? 'bg-success-500' :
                    step.status === 'processing' ? 'bg-primary-500' :
                    'bg-gray-300'
                  }`} />
                  <div className="text-gray-700">
                    {step.label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={handleContinue}
            className="w-full bg-primary-600 hover:bg-primary-700 text-white text-xl font-semibold py-4 px-8 rounded-lg transition-colors duration-200"
          >
            Continue to Preview
          </button>
        </div>
      </div>
    </div>
  );
}
