import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArtifactService } from '../services/ArtifactService';
import { ProfileService } from '../services/ProfileService';
import ArtifactPreview, { type PreviewStatus } from '../components/ArtifactPreview';
import type { ArtifactTemplate, ProfileDetails, ProfileSummary } from '../types';

type PreviewKind = 'template' | 'artifact';
type ExportStatus = '' | 'markdown' | 'docx';

function slugify(value: string): string {
  const slug = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return slug || 'artifact';
}

export default function ArtifactWorkspacePage() {
  const navigate = useNavigate();

  const [profiles, setProfiles] = useState<ProfileSummary[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [profileDetails, setProfileDetails] = useState<ProfileDetails | null>(null);
  const [templates, setTemplates] = useState<ArtifactTemplate[]>([]);
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const [loadingTemplates, setLoadingTemplates] = useState(true);

  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [selectedArtifactId, setSelectedArtifactId] = useState('');
  const [previewKind, setPreviewKind] = useState<PreviewKind>('template');

  const [previewContent, setPreviewContent] = useState('');
  const [previewStatus, setPreviewStatus] = useState<PreviewStatus>('idle');
  const [previewSourceCount, setPreviewSourceCount] = useState<number | null>(null);
  const [previewError, setPreviewError] = useState('');

  const [generating, setGenerating] = useState(false);
  const [exporting, setExporting] = useState<ExportStatus>('');
  const [errorMessage, setErrorMessage] = useState('');
  const [profileError, setProfileError] = useState('');

  const renderTemplatePreview = (profileId: string, templateId: string) => {
    setSelectedTemplateId(templateId);
    setSelectedArtifactId('');
    setPreviewKind('template');
    setPreviewContent('');
    setPreviewSourceCount(null);
    setPreviewStatus('loading');
    setPreviewError('');
    setErrorMessage('');
    ArtifactService.getInstance()
      .previewTemplate(templateId, profileId)
      .then((result) => {
        setPreviewContent(result.markdown);
        setPreviewSourceCount(result.source_count);
        setPreviewStatus('ready');
      })
      .catch((err) => {
        setPreviewStatus('error');
        setPreviewError(err instanceof Error ? err.message : 'Failed to render template preview');
      });
  };

  const renderArtifactPreview = (profileId: string, artifactId: string) => {
    setSelectedArtifactId(artifactId);
    setSelectedTemplateId('');
    setPreviewKind('artifact');
    setPreviewContent('');
    setPreviewSourceCount(null);
    setPreviewStatus('loading');
    setPreviewError('');
    setErrorMessage('');
    ArtifactService.getInstance()
      .generateMarkdown(profileId, artifactId)
      .then((content) => {
        setPreviewContent(content);
        setPreviewStatus('ready');
      })
      .catch((err) => {
        setPreviewStatus('error');
        setPreviewError(err instanceof Error ? err.message : 'Failed to generate preview');
      });
  };

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
        const initialTemplate =
          templates.find((t) => t.artifactType === 'CV')?.id ?? templates[0]?.id;
        if (initialTemplate) {
          renderTemplatePreview(profileId, initialTemplate);
        }
      })
      .catch(() => {
        setProfileError('Failed to load profile details. Please try again.');
      });
  };

  const loadProfileDetails = (profileId: string) => {
    ArtifactService.getInstance()
      .getProfile(profileId)
      .then((details) => setProfileDetails(details))
      .catch(() => {});
  };

  useEffect(() => {
    const service = ArtifactService.getInstance();
    let initialProfileId = '';

    Promise.all([
      service.getTemplates().then((list) => {
        setTemplates(list);
        return list;
      }),
      ProfileService.getInstance()
        .getProfiles()
        .then((list) => {
          setProfiles(list);
          return list;
        }),
    ])
      .then(([templateList, profileList]) => {
        if (profileList.length > 0) {
          initialProfileId = profileList[0].id;
          setSelectedProfileId(initialProfileId);
          const initialTemplate =
            templateList.find((t) => t.artifactType === 'CV')?.id ?? templateList[0]?.id;
          if (initialTemplate) {
            return service.getProfile(initialProfileId).then((details) => ({
              details,
              initialTemplate,
            }));
          }
          return null;
        }
        return null;
      })
      .then((loaded) => {
        if (loaded) {
          setProfileDetails(loaded.details);
          renderTemplatePreview(initialProfileId, loaded.initialTemplate);
        }
      })
      .catch(() => {
        setErrorMessage('Unable to load profiles. Please ensure the backend is running.');
      })
      .finally(() => {
        setLoadingProfiles(false);
        setLoadingTemplates(false);
      });
  }, []);

  const handleProfileChange = (profileId: string) => {
    setSelectedProfileId(profileId);
    loadProfile(profileId);
  };

  const handleSelectTemplate = (templateId: string) => {
    if (!selectedProfileId) return;
    renderTemplatePreview(selectedProfileId, templateId);
  };

  const handleSelectArtifact = (artifactId: string) => {
    if (!selectedProfileId) return;
    renderArtifactPreview(selectedProfileId, artifactId);
  };

  const handleRefreshPreview = () => {
    if (!selectedProfileId) return;
    if (previewKind === 'template' && selectedTemplateId) {
      renderTemplatePreview(selectedProfileId, selectedTemplateId);
    } else if (previewKind === 'artifact' && selectedArtifactId) {
      renderArtifactPreview(selectedProfileId, selectedArtifactId);
    }
  };

  const handleGenerateResume = (templateId: string) => {
    if (!selectedProfileId) return;
    setGenerating(true);
    setErrorMessage('');
    ArtifactService.getInstance()
      .createArtifact(selectedProfileId, templateId)
      .then((result) => {
        setSelectedArtifactId(result.artifactId);
        setSelectedTemplateId('');
        setPreviewKind('artifact');
        setPreviewContent('');
        setPreviewStatus('loading');
        return ArtifactService.getInstance().generateMarkdown(selectedProfileId, result.artifactId);
      })
      .then((content) => {
        setPreviewContent(content);
        setPreviewStatus('ready');
      })
      .catch((err) => {
        setPreviewStatus('error');
        setPreviewError(err instanceof Error ? err.message : 'Failed to generate resume');
      })
      .finally(() => {
        setGenerating(false);
        loadProfileDetails(selectedProfileId);
      });
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
        const active = template.id === selectedTemplateId;
        return (
          <button
            key={template.id}
            onClick={() => handleSelectTemplate(template.id)}
            className={`text-left bg-white border rounded-lg p-4 shadow-sm transition-colors ${
              active
                ? 'border-blue-500 ring-2 ring-blue-100'
                : 'border-gray-200 hover:border-blue-400'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-semibold text-gray-900">{template.displayName}</span>
              {existing && (
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                    existing.status === 'stale'
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-green-100 text-green-800'
                  }`}
                >
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
          No artifacts yet. Preview a template and click &quot;Generate Resume&quot;.
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
                  active
                    ? 'bg-blue-50 border-l-4 border-blue-500'
                    : 'hover:bg-gray-50 border-l-4 border-transparent'
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

  const renderPreviewPanel = () => {
    const isTemplate = previewKind === 'template';
    const selectedTemplate = templates.find((t) => t.id === selectedTemplateId) ?? null;
    const existingArtifact = selectedTemplate
      ? profileDetails?.artifacts.find((a) => a.type === selectedTemplate.artifactType)
      : undefined;

    const toolbar = (
      <>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleRefreshPreview}
            className="inline-flex items-center px-4 py-2 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 font-semibold text-sm transition-colors duration-200"
          >
            Refresh Preview
          </button>
          {isTemplate && selectedTemplate ? (
            <button
              onClick={() => handleGenerateResume(selectedTemplate.id)}
              disabled={Boolean(existingArtifact) || generating}
              className="inline-flex items-center px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors duration-200"
            >
              {generating ? 'Generating...' : 'Generate Resume'}
            </button>
          ) : (
            <>
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
            </>
          )}
        </div>
        {isTemplate && existingArtifact && (
          <span className="text-xs text-amber-700">
            {existingArtifact.status === 'stale'
              ? 'The existing artifact is stale. Regenerate it from the artifacts list.'
              : 'An artifact for this template already exists — view it in the artifacts list.'}
          </span>
        )}
      </>
    );

    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-gray-900">
            {isTemplate ? 'Resume Preview' : 'Generated Resume'}
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            {isTemplate
              ? 'Rendered on demand from the current profile through the generation pipeline.'
              : 'Generated on demand from the canonical profile by the backend generation pipeline.'}
          </p>
        </div>
        <div className="border border-gray-200 rounded-md bg-gray-50 p-5 min-h-64 max-h-[600px] overflow-y-auto">
          <ArtifactPreview
            status={previewStatus}
            content={previewContent}
            emptyMessage="Select a template to preview your resume, then generate it."
            errorMessage={previewError}
            sourceCount={previewSourceCount}
            toolbar={previewStatus === 'ready' ? toolbar : undefined}
            onRetry={handleRefreshPreview}
          />
        </div>
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
                  <h2 className="text-xl font-semibold text-gray-900">Resume Templates</h2>
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

            {/* Right column: preview */}
            <div className="lg:col-span-2 space-y-6">{renderPreviewPanel()}</div>
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
