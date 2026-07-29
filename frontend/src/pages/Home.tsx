import { useNavigate } from 'react-router-dom';

export default function Home() {
  const navigate = useNavigate();

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
            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
              Backend Connected
            </span>
            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
              Demo Ready
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
