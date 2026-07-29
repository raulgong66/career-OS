import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ProfileService } from '../services/ProfileService';

type BackendStatus = 'checking' | 'connected' | 'disconnected';

export default function Home() {
  const navigate = useNavigate();
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking');
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState('');
  const [profileCount, setProfileCount] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const service = ProfileService.getInstance();
    service.getProfiles()
      .then((profiles) => {
        setBackendStatus('connected');
        setProfileCount(profiles.length);
      })
      .catch(() => {
        setBackendStatus('disconnected');
      });
  }, []);

  const handleImportProfile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setImportError('');

    try {
      const service = ProfileService.getInstance();
      const result = await service.uploadProfile(file);
      setProfileCount((prev) => prev + 1);
      alert(`Profile imported: ${result.profile.name}`);
    } catch (error) {
      setImportError(
        error instanceof Error ? error.message : 'Failed to import profile'
      );
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const statusBadge = () => {
    switch (backendStatus) {
      case 'checking':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
            Checking Backend...
          </span>
        );
      case 'connected':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
            Backend Connected ({profileCount} profiles)
          </span>
        );
      case 'disconnected':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800">
            Backend Disconnected
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-8">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-4xl font-bold text-gray-900">CareerOS Platform Alpha</h1>
          <p className="text-lg text-gray-600 mt-2">AI-powered career operating system</p>
        </div>
      </header>

      <main className="flex-1 px-6 py-12">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">Resume Generation</h2>
                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                  READY
                </span>
              </div>
              <p className="text-sm text-gray-600 mb-4">
                Generate professional career artifacts from a structured profile.
              </p>
            </div>

            <div className="bg-white border-2 border-blue-500 rounded-lg p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">AI Tailoring</h2>
                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                  READY
                </span>
              </div>
              <p className="text-sm text-gray-600 mb-4">
                Tailor resumes to a specific job description using AI recommendations.
              </p>
              <button
                onClick={() => navigate('/tailoring')}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-md transition-colors duration-200"
              >
                Open Demo
              </button>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">Architecture</h2>
                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                  READY
                </span>
              </div>
              <p className="text-sm text-gray-600 mb-4">
                Backend API, AI Generator, Recommendation Engine
              </p>
            </div>
          </div>

          {/* Profile Import */}
          <div className="mt-8 bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">Profile Management</h2>
                <p className="text-sm text-gray-600 mt-1">
                  Import a CV document (.docx, .doc, .txt) to create a canonical profile
                </p>
              </div>
              {backendStatus === 'connected' && (
                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                  {profileCount} profile{(profileCount !== 1 ? 's' : '')} available
                </span>
              )}
            </div>
            <div className="flex items-center gap-4">
              <input
                ref={fileInputRef}
                type="file"
                accept=".docx,.doc,.txt"
                onChange={handleImportProfile}
                disabled={importing || backendStatus !== 'connected'}
                className="block text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed"
              />
              {importing && (
                <span className="text-sm text-blue-600">Importing...</span>
              )}
            </div>
            {importError && (
              <p className="mt-2 text-sm text-red-600">{importError}</p>
            )}
          </div>

          <div className="mt-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Future Modules</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="bg-gray-100 border border-gray-200 rounded-lg p-6 opacity-60">
                <h2 className="text-xl font-semibold text-gray-900 mb-2">Interview Preparation</h2>
                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-200 text-gray-700">
                  COMING NEXT
                </span>
              </div>

              <div className="bg-gray-100 border border-gray-200 rounded-lg p-6 opacity-60">
                <h2 className="text-xl font-semibold text-gray-900 mb-2">Career Analytics</h2>
                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-200 text-gray-700">
                  COMING NEXT
                </span>
              </div>

              <div className="bg-gray-100 border border-gray-200 rounded-lg p-6 opacity-60">
                <h2 className="text-xl font-semibold text-gray-900 mb-2">Learning Planner</h2>
                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-200 text-gray-700">
                  COMING NEXT
                </span>
              </div>

              <div className="bg-gray-100 border border-gray-200 rounded-lg p-6 opacity-60">
                <h2 className="text-xl font-semibold text-gray-900 mb-2">Application Tracking</h2>
                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-200 text-gray-700">
                  COMING NEXT
                </span>
              </div>

              <div className="bg-gray-100 border border-gray-200 rounded-lg p-6 opacity-60">
                <h2 className="text-xl font-semibold text-gray-900 mb-2">Skill Gap Analysis</h2>
                <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-200 text-gray-700">
                  COMING NEXT
                </span>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <span className="text-sm text-gray-600">Platform Alpha</span>
            {statusBadge()}
            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
              Demo Ready
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
