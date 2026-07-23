import { useNavigate } from 'react-router-dom';

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-4">
      <div className="max-w-2xl text-center">
        <h1 className="text-6xl font-bold text-gray-900 mb-4">
          CareerOS
        </h1>
        <p className="text-2xl text-gray-600 mb-12">
          Professional Knowledge Platform
        </p>
        <button
          onClick={() => navigate('/tailor')}
          className="bg-primary-600 hover:bg-primary-700 text-white text-xl font-semibold py-4 px-12 rounded-lg transition-colors duration-200"
        >
          Start
        </button>
      </div>
    </div>
  );
}
