import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import TailoringPage from './pages/TailoringPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/tailoring" element={<TailoringPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
