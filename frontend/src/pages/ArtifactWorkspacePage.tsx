import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArtifactService } from '../services/ArtifactService';
import { ProfileService } from '../services/ProfileService';
import type { ArtifactTemplate, ProfileDetails, ProfileSummary } from '../types';

type PreviewStatus = 'idle' | 'loading' | 'ready' | 'error';
type ExportStatus = '' | 'markdown' | 'docx';

function slugify(value: string): string {
  const slug = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return slug || 'artifact';
}

function renderMarkdown(content: string) {
  const lines = content.split('\n');
  return lines.map((line, index) => {
    if (line.startsWith('### ')) {
      return <h5 key={index} className="text-sm font-semibold text-gray-900 mt-3 mb-1">{line.slice(4)}</h5>;
    }
    if (line.startsWith('## ')) {
      return <h4 key={index} className="text-base font-semibold text-gray-900 mt-4 mb-1.5">{line.slice(3)}</h4>;
    }
    if (line.startsWith('# ')) {
      return <h3 key={index} className="text-lg font-bold text-gray-900 mt-5 mb-2">{line.slice(2)}</h3>;
    }
    if (line.startsWith('- ')) {
      return <li key={index} className="text-sm text-gray-700 ml-5">{line.slice(2)}</li>;
    }
    if (line.trim()) {
      return <p key={index} className="text-sm text-gray-700 mb-1.5 leading-relaxed">{line}</p>;
    }
    return <div key={index} className="h-2" />;
  });
}

export default function ArtifactWorkspacePage() {
  const navigate = useNavigate();

  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [profileDetails, setProfileDetails] = useState<ProfileDetails | null>(null);
  const [templates, setTemplates] = useState<ArtifactTemplate[]>([]);
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [selectedArtifactId, setSelectedArtifactId] = useState('');
  const [previewContent, setPreviewContent] = useState('');
  const [previewStatus, setPreviewStatus] = useState<PreviewStatus>('idle');
  const [creatingTemplateId, setCreatingTemplateId] = useState('');
  const [exporting, setExporting] = useState<ExportStatus>('');
  const [errorMessage, setErrorMessage] = useState('');
  const [profileError, setProfileError] = useState('');

  const loadProfile = (profileId: string) => {
    setProfileDetails(null);
    setSelectedArtifactId('');
    setPreviewContent('');
    setPreviewStatus('idle');
    setProfileError('');
    ArtifactService.getInstance()
      .getProfile(profileId)
      .then((details) => {
        setProfileDetails(details);
        if (details.artifacts.length > 0) {
          setSelectedArtifactId(details.artifacts[0].id);
          setPreviewStatus('loading');
          ArtifactService.getInstance()
            .generateMarkdown(profileId, details.artifacts[0].id)
            .then((content) => {
              setPreviewContent(content);
              setPreviewStatus('ready');
            })
            .catch((err) => {
              setPreviewStatus('error');
              setErrorMessage(err instanceof Error ? err.message : 'Failed to generate preview');
            });
        }
      })
      .catch(() => {
        setProfileError('Failed to load profile details. Please try again.');
      });
  };

  useEffect(() => {
    const service = ArtifactService.getInstance();
    service
      .getTemplates()
      .then((list) => setTemplates(list))
      .catch(() => setTemplates([]))
      .finally(() => setLoadingTemplates(false));

    ProfileService.getInstance()
      .getProfiles()
      .then((list) => {
        setProfiles(list);
        if (list.length > 0) {
          setSelectedProfileId(list[0].id);
          loadProfile(list[0].id);
        }
      })
      .catch(() => {
        setErrorMessage('Unable to load profiles. Please ensure the backend is running.');
      })
      .finally(() => setLoadingProfiles(false));
  }, []);

  const handleProfileChange = (profileId: string) => {
    setSelectedProfileId(profileId);
    loadProfile(profileId);
  };

  const handleSelectArtifact = (artifactId: string) => {
    if (!selectedProfileId) return;
    setSelectedArtifactId(artifactId);
    setPreviewContent('');
    setPreviewStatus('loading');
    setErrorMessage('');
    ArtifactService.getInstance()
      .generateMarkdown(selectedProfileId, artifactId)
      .then((content) => {
        setPreviewContent(content);
        setPreviewStatus('ready');
      })
      .catch((err) => {
        setPreviewStatus('error');
        setErrorMessage(err instanceof Error ? err.message : 'Failed to generate preview');
      });
  };

  const handleCreateArtifact = (templateId: string) => {
    if (!selectedProfileId) return;
    setCreatingTemplateId(templateId);
    setErrorMessage('');
    ArtifactService.getInstance()
      .createArtifact(selectedProfileId, templateId)
      .then((result) => {
        loadProfile(selectedProfileId);
        setSelectedArtifactId(result.artifactId);
      })
      .catch((err) => {
        setErrorMessage(err instanceof Error ? err.message : 'Failed to create artifact');
      })
      .finally(() => setCreatingTemplateId(''));
  };

  const handleExport = async (format: 'markdown' | 'docx') => {
    if (!selectedProfileId || !selectedArtifactId) return;
    setExporting(format);
    setErrorMessage('');
    try {
      const artifact = profileDetails?.artifacts.find((a) => a.id === selectedArtifactId);
      const baseName = slugify(artifact?.name ?? artifact?.type ?? selectedArtifactId);
      const service = ArtifactService.getInstance();
      if (format === 'markdown') {
        const content = await service.generateMarkdown(selectedProfileId, selectedArtifactId);
        service.downloadBlob(new Blob([content], { type: 'text/markdown' }), `${baseName}.md`);
      } else {
        const blob = await service.generateDocx(selectedProfileId, selectedArtifactId);
        service.downloadBlob(blob, `${baseName}.docx`);
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to export artifact');
    } finally {
      setExporting('');
    }
  };

  const renderTemplateGrid = () => (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {templates.map((template) => {
        const existing = profileDetails?.artifacts.find((a) => a.type === template.artifactType);
        const disabled = Boolean(existing) || creatingTemplateId === template.id;
        return (
          <button
            key={template.id}
            onClick={() => handleCreateArtifact(template.id)}
            disabled={disabled}
            className="text-left bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:border-blue-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-semibold text-gray-900">{template.displayName}</span>
              {existing && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                  {existing.status === 'stale' ? 'STALE' : 'EXISTS'}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500">{template.artifactType}</p>
          </button>
        );
      })}
    </div>
  );

  const renderArtifactList = () => {
    if (!profileDetails) return null;
    if (profileDetails.artifacts.length === 0) {
      return (
        <p className="text-sm text-gray-400 italic">
          No artifacts defined yet. Create one from a template above.
        </p>
      );
    }
    return (
      <ul className="divide-y divide-gray-200 border border-gray-200 rounded-md overflow-hidden">
        {profileDetails.artifacts.map((artifact) => {
          const active = artifact.id === selectedArtifactId;
          return (
            <li key={artifact.id}>
              <button
                onClick={() => handleSelectArtifact(artifact.id)}
                className={`w-full text-left px-3 py-2.5 transition-colors ${
                  active ? 'bg-blue-50 border-l-4 border-blue-500' : 'hover:bg-gray-50 border-l-4 border-transparent'
                }`}
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-900">{artifact.name || artifact.type || artifact.id}</p>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      artifact.status === 'stale'
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-green-100 text-green-800'
                    }`}
                  >
                    {artifact.status}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-gray-500">{artifact.type || 'UNKNOWN'}</span>
                  <span className="text-xs text-gray-400">{artifact.id}</span>
                  <span className="text-xs text-gray-400">· {artifact.sourceCount} sources</span>
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    );
  };

  const renderPreview = () => {
    if (!selectedArtifactId) {
      return (
        <div className="flex items-center justify-center h-64 text-sm text-gray-400">
          Select an artifact to preview its generated content.
        </div>
      );
    }
    if (previewStatus === 'loading') {
      return (
        <div className="flex flex-col items-center justify-center h-64 text-gray-400">
          <svg className="animate-spin h-8 w-8 mb-3 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-sm">Generating preview...</p>
        </div>
      );
    }
    if (previewStatus === 'error') {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <p className="text-sm text-red-700 mb-3">Failed to generate preview.</p>
            <button
              onClick={() => handleSelectArtifact(selectedArtifactId)}
              className="inline-flex items-center px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm transition-colors duration-200"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return (
      <div className="space-y-1">
        {renderMarkdown(previewContent)}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 px-6 py-8">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-gray-900">CareerOS Platform Alpha</h1>
            <p className="text-lg text-gray-600 mt-2">Resume Generation Workspace</p>
          </div>
          <button
            onClick={() => navigate('/')}
            className="text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            ← Back to Home
          </button>
        </div>
      </header>

      <main className="flex-1 px-6 py-8">
        <div className="max-w-6xl mx-auto space-y-6">
          {errorMessage && (
            <div className="border border-red-200 bg-red-50 rounded-md p-4 text-sm text-red-700">{errorMessage}</div>
          )}
          {profileError && (
            <div className="border border-amber-200 bg-amber-50 rounded-md p-4 text-sm text-amber-800">{profileError}</div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left column: profile + templates + artifacts */}
            <div className="space-y-6">
              <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-gray-900">Profile</h2>
                  <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                    READY
                  </span>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Profile</label>
                  <select
                    value={selectedProfileId}
                    onChange={(e) => handleProfileChange(e.target.value)}
                    disabled={loadingProfiles}
                    className="w-full p-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {loadingProfiles && <option value="">Loading profiles...</option>}
                    {profiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>
                {profileDetails && (
                  <div className="mt-4 border border-gray-200 rounded-md divide-y divide-gray-200">
                    <div className="px-3 py-2">
                      <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Headline</label>
                      <p className="mt-0.5 text-sm text-gray-700">{profileDetails.person.headline || '—'}</p>
                    </div>
                    <div className="px-3 py-2">
                      <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide">Artifacts</label>
                      <p className="mt-0.5 text-sm text-gray-700">
                        {profileDetails.artifacts.length} artifact{(profileDetails.artifacts.length !== 1 ? 's' : '')} defined
                      </p>
                    </div>
                  </div>
                )}
              </div>

              <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-gray-900">Generate</h2>
                  <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                    {templates.length} TEMPLATES
                  </span>
                </div>
                {loadingTemplates ? (
                  <p className="text-sm text-gray-400">Loading templates...</p>
                ) : templates.length === 0 ? (
                  <p className="text-sm text-gray-400 italic">No templates available.</p>
                ) : (
                  renderTemplateGrid()
                )}
              </div>

              <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-gray-900">Artifacts</h2>
                  <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                    {profileDetails?.artifacts.length ?? 0}
                  </span>
                </div>
                {renderArtifactList()}
              </div>
            </div>

            {/* Right column: preview + export */}
            <div className="lg:col-span-2 space-y-6">
              <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-semibold text-gray-900">Preview</h2>
                    <p className="text-sm text-gray-600 mt-1">
                      Generated on demand from the canonical profile by the backend generation pipeline.
                    </p>
                  </div>
                  {selectedArtifactId && previewStatus === 'ready' && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleExport('markdown')}
                        disabled={exporting !== ''}
                        className="inline-flex items-center px-4 py-2 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed font-semibold text-sm transition-colors duration-200"
                      >
                        {exporting === 'markdown' ? 'Exporting...' : 'Export .md'}
                      </button>
                      <button
                        onClick={() => handleExport('docx')}
                        disabled={exporting !== ''}
                        className="inline-flex items-center px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors duration-200"
                      >
                        {exporting === 'docx' ? 'Exporting...' : 'Export .docx'}
                      </button>
                    </div>
                  )}
                </div>
                <div className="border border-gray-200 rounded-md bg-gray-50 p-5 min-h-64 max-h-[600px] overflow-y-auto">
                  {renderPreview()}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className="bg-white border-t border-gray-200 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <span className="text-sm text-gray-600">Platform Alpha · Resume Generation Workspace</span>
          <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
            Demo Ready
          </span>
        </div>
      </footer>
    </div>
  );
}
