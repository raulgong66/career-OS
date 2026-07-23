import { useNavigate, useLocation } from 'react-router-dom';
import { DocumentService } from '../services/DocumentService';
import type { Profile } from '../types';

export default function Preview() {
  const navigate = useNavigate();
  const location = useLocation();
  const { profile } = location.state as { profile: Profile };

  const handleDownloadDocx = async () => {
    const blob = await DocumentService.getInstance().downloadDocx(profile.artifacts[0].id);
    DocumentService.getInstance().downloadBlob(blob, `${profile.person.firstName}_${profile.person.lastName}_CV.docx`);
  };

  const handleDownloadPdf = async () => {
    const blob = await DocumentService.getInstance().downloadPdf(profile.artifacts[0].id);
    DocumentService.getInstance().downloadBlob(blob, `${profile.person.firstName}_${profile.person.lastName}_CV.pdf`);
  };

  return (
    <div className="min-h-screen bg-white px-4 py-12">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-900 mb-8">
          Preview
        </h1>

        <div className="bg-gray-50 rounded-xl p-8 mb-8">
          <div className="aspect-[8.5/11] bg-white border border-gray-200 rounded-lg flex items-center justify-center">
            <div className="text-center text-gray-400">
              <div className="text-6xl mb-4">📄</div>
              <div className="text-xl">Document Preview Placeholder</div>
              <div className="text-sm mt-2">
                Tailored CV for {profile.person.firstName} {profile.person.lastName}
              </div>
            </div>
          </div>
        </div>

        <div className="flex space-x-4">
          <button
            onClick={handleDownloadDocx}
            className="flex-1 bg-primary-600 hover:bg-primary-700 text-white text-xl font-semibold py-4 px-8 rounded-lg transition-colors duration-200"
          >
            Download DOCX
          </button>
          <button
            onClick={handleDownloadPdf}
            className="flex-1 bg-primary-600 hover:bg-primary-700 text-white text-xl font-semibold py-4 px-8 rounded-lg transition-colors duration-200"
          >
            Download PDF
          </button>
        </div>

        <button
          onClick={() => navigate('/tailor')}
          className="w-full mt-4 bg-gray-200 hover:bg-gray-300 text-gray-700 text-xl font-semibold py-4 px-8 rounded-lg transition-colors duration-200"
        >
          Back
        </button>
      </div>
    </div>
  );
}
