import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import TailoringPage from './pages/TailoringPage';
import InterviewPracticePage from './pages/InterviewPracticePage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/tailoring" element={<TailoringPage />} />
        <Route path="/interviews/practice" element={<InterviewPracticePage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
