import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import DiagnosisPage from './pages/DiagnosisPage'
import HistoryPage from './pages/HistoryPage'
import AdminPage from './pages/AdminPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<DiagnosisPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="admin" element={<AdminPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
