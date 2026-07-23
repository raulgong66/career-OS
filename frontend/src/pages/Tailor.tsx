import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ProfileService } from '../services/ProfileService';
import { TailoringService } from '../services/TailoringService';
import type { Profile } from '../types';

export default function Tailor() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const uploadedProfile = await ProfileService.getInstance().uploadProfile(file);
      setProfile(uploadedProfile);
    }
  };

  const handleAnalyze = async () => {
    if (!profile || !jobDescription.trim()) return;
    
    setIsAnalyzing(true);
    const result = await TailoringService.getInstance().analyzeAndTailor({
      profile,
      artifactId: profile.artifacts[0].id,
      jobDescription,
    });
    setIsAnalyzing(false);
    
    navigate('/analysis', { state: { result, profile } });
  };

  return (
    <div className="min-h-screen bg-white px-4 py-12">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-900 mb-8">
          Tailor Application
        </h1>

        <div className="space-y-8">
          <div className="bg-gray-50 rounded-xl p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Master Profile
            </h2>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
              <input
                type="file"
                accept=".json,.yaml,.yml"
                onChange={handleFileUpload}
                className="hidden"
                id="profile-upload"
              />
              <label
                htmlFor="profile-upload"
                className="cursor-pointer"
              >
                {profile ? (
                  <div className="text-success-600 font-semibold">
                    ✓ Profile loaded: {profile.person.firstName} {profile.person.lastName}
                  </div>
                ) : (
                  <div className="text-gray-600">
                    Click to upload profile (JSON or YAML)
                  </div>
                )}
              </label>
            </div>
          </div>

          <div className="bg-gray-50 rounded-xl p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Job Opportunity
            </h2>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste job description here..."
              className="w-full h-48 p-4 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          <button
            onClick={handleAnalyze}
            disabled={!profile || !jobDescription.trim() || isAnalyzing}
            className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-xl font-semibold py-4 px-8 rounded-lg transition-colors duration-200"
          >
            {isAnalyzing ? 'Analyzing...' : 'Analyze & Tailor'}
          </button>
        </div>
      </div>
    </div>
  );
}
