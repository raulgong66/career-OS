import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Tailor from './pages/Tailor';
import Analysis from './pages/Analysis';
import Preview from './pages/Preview';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/tailor" element={<Tailor />} />
        <Route path="/analysis" element={<Analysis />} />
        <Route path="/preview" element={<Preview />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
