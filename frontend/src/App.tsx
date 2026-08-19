import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import TailoringPage from './pages/TailoringPage';
import InterviewPracticePage from './pages/InterviewPracticePage';
import ArtifactWorkspacePage from './pages/ArtifactWorkspacePage';
import CareerKnowledgePage from './pages/CareerKnowledgePage';
import MissionPage from './pages/MissionPage';
import TransformationPage from './pages/TransformationPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/mission" element={<MissionPage />} />
        <Route path="/transformation" element={<TransformationPage />} />
        <Route path="/tailoring" element={<TailoringPage />} />
        <Route path="/interviews/practice" element={<InterviewPracticePage />} />
        <Route path="/artifacts" element={<ArtifactWorkspacePage />} />
        <Route path="/knowledge" element={<CareerKnowledgePage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
