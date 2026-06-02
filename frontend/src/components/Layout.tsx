import { NavLink, Outlet } from 'react-router-dom'
import { Activity, History, Settings, Stethoscope } from 'lucide-react'

const nav = [
  { to: '/', label: 'Chẩn đoán', icon: Stethoscope },
  { to: '/history', label: 'Lịch sử', icon: History },
  { to: '/admin', label: 'Quản trị', icon: Settings },
]

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-7 h-7 text-primary-600" />
            <div>
              <h1 className="text-lg font-bold text-primary-700">MedAI</h1>
              <p className="text-xs text-gray-500">Gợi ý chẩn đoán tuyến cơ sở</p>
            </div>
          </div>
          <nav className="flex gap-1">
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`
                }
              >
                <Icon className="w-4 h-4" />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6">
        <Outlet />
      </main>

      <footer className="border-t bg-white py-3 text-center text-xs text-gray-400">
        MedAI v1.0 — Hỗ trợ chẩn đoán sơ bộ, không thay thế bác sĩ
      </footer>
    </div>
  )
}
