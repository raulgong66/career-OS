import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ProfileService } from '../services/ProfileService';

type BackendStatus = 'checking' | 'connected' | 'disconnected';

interface PrimaryModule {
  title: string;
  description: string;
  to: string;
}

const primaryModules: PrimaryModule[] = [
  {
    title: 'Resume Workspace',
    description: 'Generate professional career artifacts from a structured profile.',
    to: '/artifacts',
  },
  {
    title: 'AI Tailoring',
    description: 'Tailor resumes to a specific job description using AI recommendations.',
    to: '/tailoring',
  },
  {
    title: 'Interview Preparation',
    description: 'Practice with a deterministic, evidence-backed interview session.',
    to: '/interviews/practice',
  },
  {
    title: 'Career Knowledge',
    description: 'Ask CareerOS about itself using the Career Self Knowledge System.',
    to: '/knowledge',
  },
];

const comingNextModules = [
  'Career Analytics',
  'Learning Planner',
  'Application Tracking',
  'Skill Gap Analysis',
];

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
    <div className="min-h-screen bg-blue-50 flex flex-col">
      <header className="bg-white border-b border-blue-100 px-6 py-10">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-4xl font-bold text-gray-900">CareerOS Platform Alpha</h1>
          <p className="text-lg text-gray-600 mt-2">AI-powered career operating system</p>
        </div>
      </header>

      <main className="flex-1 px-6 py-16">
        <div className="max-w-6xl mx-auto space-y-16">
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Primary Modules</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {primaryModules.map((module) => (
                <div key={module.title} className="bg-white border-2 border-blue-500 rounded-lg p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xl font-semibold text-gray-900">{module.title}</h3>
                    <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                      READY
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mb-4">{module.description}</p>
                  <button
                    onClick={() => navigate(module.to)}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-md transition-colors duration-200"
                  >
                    Open Demo
                  </button>
                </div>
              ))}
            </div>
          </section>

          {/* Profile Import */}
          <section className="bg-white border border-blue-100 rounded-lg p-6 shadow-sm">
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
          </section>

          {/* Coming Next */}
          <section className="bg-blue-100/40 border border-blue-200/70 rounded-lg p-8">
            <h2 className="text-lg font-semibold text-gray-700 mb-6">Coming Next</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {comingNextModules.map((module) => (
                <div key={module} className="bg-white/70 border border-blue-100 rounded-lg p-6 opacity-60">
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">{module}</h3>
                  <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-700">
                    COMING NEXT
                  </span>
                </div>
              ))}
            </div>
          </section>
        </div>
      </main>

      <footer className="bg-white border-t border-blue-100 px-6 py-4">
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
