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
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
            Checking Backend...
          </span>
        );
      case 'connected':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
            Backend Connected ({profileCount} profiles)
          </span>
        );
      case 'disconnected':
        return (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
            Backend Disconnected
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F9FF] flex flex-col">
      {/* Hero */}
      <header className="relative overflow-hidden bg-gradient-to-b from-primary-900 via-primary-600 to-[#F5F9FF] px-6 xl:px-10 2xl:px-16 pt-10 pb-24">
        <div className="absolute -top-32 -left-32 h-96 w-96 rounded-full bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.14),transparent_70%)] pointer-events-none" aria-hidden="true" />
        <div className="absolute top-1/3 right-1/4 h-80 w-80 rounded-full bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.10),transparent_70%)] pointer-events-none" aria-hidden="true" />
        <div className="absolute bottom-0 left-1/3 h-72 w-72 rounded-full bg-[radial-gradient(circle_at_center,rgba(147,197,253,0.18),transparent_70%)] pointer-events-none" aria-hidden="true" />
        <div className="absolute right-0 -top-16 h-[34rem] w-[34rem] translate-x-1/3 pointer-events-none opacity-15" aria-hidden="true">
          <div className="absolute left-1/2 top-1/2 h-[34rem] w-[34rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/40" />
          <div className="absolute left-1/2 top-1/2 h-[27rem] w-[27rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/30" />
          <div className="absolute left-1/2 top-1/2 h-[20rem] w-[20rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/25" />
          <div className="absolute left-1/2 top-1/2 h-[13rem] w-[13rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/20" />
          <div className="absolute left-1/2 top-1/2 h-[7rem] w-[7rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle_at_center,rgba(147,197,253,0.45),transparent_70%)]" />
        </div>

        <div className="relative z-10 max-w-none">
          <div className="flex items-center justify-between flex-wrap gap-3 mb-10 animate-[fade-in-up_0.6s_ease-out_both]">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold text-white bg-white/15 backdrop-blur-sm border border-white/25">
              Platform Alpha
            </span>
            <div className="flex items-center gap-3">
              {statusBadge()}
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium text-white bg-white/15 backdrop-blur-sm border border-white/25">
                Demo Ready
              </span>
            </div>
          </div>
          <h1 className="text-5xl font-bold text-white tracking-tight max-w-2xl">CareerOS Platform Alpha</h1>
          <p className="text-xl text-blue-100 mt-4">AI-powered career operating system</p>
          <p className="text-base text-blue-50/90 mt-4 max-w-2xl leading-relaxed">
            Build, optimize and manage your professional future with AI-powered tools and intelligent recommendations.
          </p>
        </div>
      </header>

      <main className="flex-1 px-6 xl:px-10 2xl:px-16">
        <div className="max-w-none -mt-16 space-y-24">
          {/* Primary Modules */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-8">Primary Modules</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {primaryModules.map((module) => (
                <div
                  key={module.title}
                  className="w-full bg-white rounded-xl border border-blue-100 shadow-sm p-9 flex flex-col transition-all duration-300 ease-out hover:shadow-xl hover:shadow-blue-900/10 hover:border-blue-200 hover:-translate-y-1"
                >
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-2xl font-bold text-gray-900">{module.title}</h3>
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-50 text-green-700">
                      READY
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 leading-relaxed mb-6 flex-1">{module.description}</p>
                  <button
                    onClick={() => navigate(module.to)}
                    className="w-full bg-gradient-to-r from-blue-600 to-blue-400 hover:from-blue-700 hover:to-blue-500 text-white font-semibold py-3 px-4 rounded-lg shadow-md shadow-blue-600/20 hover:shadow-lg hover:shadow-blue-600/30 transition-all duration-300 ease-out hover:-translate-y-0.5 active:translate-y-0 active:shadow-md"
                  >
                    Open Demo
                  </button>
                </div>
              ))}
            </div>
          </section>

          {/* Profile Import */}
          <section className="bg-white rounded-xl border border-blue-100 shadow-sm p-9">
            <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Profile Management</h2>
                <p className="text-sm text-gray-500 mt-2">
                  Import a CV document (.docx, .doc, .txt) to create a canonical profile
                </p>
              </div>
              {backendStatus === 'connected' && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                  {profileCount} profile{(profileCount !== 1 ? 's' : '')} available
                </span>
              )}
            </div>
            <div className="flex items-center gap-4 flex-wrap">
              <input
                ref={fileInputRef}
                type="file"
                accept=".docx,.doc,.txt"
                onChange={handleImportProfile}
                disabled={importing || backendStatus !== 'connected'}
                className="block text-sm text-gray-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed"
              />
              {importing && (
                <span className="text-sm text-blue-600">Importing...</span>
              )}
            </div>
            {importError && (
              <p className="mt-3 text-sm text-red-600">{importError}</p>
            )}
          </section>

          {/* Coming Next */}
          <section className="rounded-3xl bg-blue-100/50 border border-blue-200/70 p-10">
            <h2 className="text-xl font-semibold text-blue-900 mb-8">Coming Next</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
              {comingNextModules.map((module) => (
                <div
                  key={module}
                  className="w-full bg-white/50 backdrop-blur-sm border border-dashed border-blue-200 rounded-xl p-6"
                >
                  <h3 className="text-lg font-semibold text-gray-700 mb-3">{module}</h3>
                  <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-100/70 text-blue-600">
                    COMING NEXT
                  </span>
                </div>
              ))}
            </div>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-primary-900 text-blue-100">
        <div className="max-w-none px-6 xl:px-10 2xl:px-16 py-6 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <p className="text-xs sm:text-sm text-blue-200 text-left">
            Built on deterministic principles • Powered by AI • Explainable • Evidence-based • User in control
          </p>
          <p className="text-xs sm:text-sm font-semibold text-white text-left md:text-right">
            CareerOS Platform Alpha • © CareerOS
          </p>
        </div>
      </footer>
    </div>
  );
}
