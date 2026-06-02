import { AlertTriangle, AlertCircle, Info } from 'lucide-react'
import type { RiskAlert } from '../types'

const levelStyle: Record<string, { bg: string; border: string; icon: typeof AlertTriangle }> = {
  'Khẩn cấp': { bg: 'bg-danger-50', border: 'border-danger-500', icon: AlertTriangle },
  'Cao': { bg: 'bg-warning-50', border: 'border-warning-500', icon: AlertCircle },
  'Trung bình': { bg: 'bg-primary-50', border: 'border-primary-500', icon: Info },
  'Thấp': { bg: 'bg-gray-50', border: 'border-gray-300', icon: Info },
}

export default function RiskAlerts({ alerts }: { alerts: RiskAlert[] }) {
  if (!alerts.length) return null

  return (
    <div className="space-y-2">
      <h3 className="font-semibold text-gray-800">Cảnh báo rủi ro</h3>
      {alerts.map((a, i) => {
        const style = levelStyle[a.level] ?? levelStyle['Thấp']
        const Icon = style.icon
        return (
          <div
            key={i}
            className={`${style.bg} border-l-4 ${style.border} rounded-r-lg p-3`}
          >
            <div className="flex items-start gap-2">
              <Icon className="w-5 h-5 shrink-0 mt-0.5" />
              <div>
                <span className="text-xs font-bold uppercase tracking-wide text-gray-600">
                  {a.level}
                </span>
                <p className="font-medium text-gray-900">{a.message}</p>
                <p className="text-sm text-gray-600 mt-1">{a.advice}</p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
