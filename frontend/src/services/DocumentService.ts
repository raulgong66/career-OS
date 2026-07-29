export class DocumentService {
  private static instance: DocumentService;

  private constructor() {}

  static getInstance(): DocumentService {
    if (!DocumentService.instance) {
      DocumentService.instance = new DocumentService();
    }
    return DocumentService.instance;
  }

  async downloadDocx(_artifactId: string): Promise<Blob> {
    // Mock implementation - in production this would call the backend API
    return new Promise((resolve) => {
      setTimeout(() => {
        const mockBlob = new Blob(['Mock DOCX content'], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
        resolve(mockBlob);
      }, 500);
    });
  }

  async downloadPdf(_artifactId: string): Promise<Blob> {
    // Mock implementation - in production this would call the backend API
    return new Promise((resolve) => {
      setTimeout(() => {
        const mockBlob = new Blob(['Mock PDF content'], { type: 'application/pdf' });
        resolve(mockBlob);
      }, 500);
    });
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
