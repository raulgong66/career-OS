const BASE = '';

export class DocumentService {
  private static instance: DocumentService;

  private constructor() {}

  static getInstance(): DocumentService {
    if (!DocumentService.instance) {
      DocumentService.instance = new DocumentService();
    }
    return DocumentService.instance;
  }

  async downloadDocx(profileId: string, artifactId: string): Promise<Blob> {
    const response = await fetch(`${BASE}/generate/artifact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile_id: profileId,
        artifact_id: artifactId,
        output_format: 'docx',
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to generate DOCX: ${response.status} ${response.statusText}`);
    }

    return response.blob();
  }

  async downloadPdf(profileId: string, artifactId: string): Promise<Blob> {
    const response = await fetch(`${BASE}/generate/artifact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile_id: profileId,
        artifact_id: artifactId,
        output_format: 'docx',
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to generate PDF: ${response.status} ${response.statusText}`);
    }

    return response.blob();
  }

  downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }
}
