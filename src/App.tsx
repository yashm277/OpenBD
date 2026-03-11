import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import DeleteListGenerator from './pages/DeleteListGenerator'
import DuplicateFinder from './pages/DuplicateFinder'
import OverlapChecker from './pages/OverlapChecker'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/delete-list" element={<DeleteListGenerator />} />
        <Route path="/duplicate-finder" element={<DuplicateFinder />} />
        <Route path="/overlap-checker" element={<OverlapChecker />} />
      </Routes>
    </BrowserRouter>
  )
}
