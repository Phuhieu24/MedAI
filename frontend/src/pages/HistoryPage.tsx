import { useState } from 'react'
import { Search, Loader2, ChevronRight } from 'lucide-react'
import { getPatientHistory, getSessionDetail } from '../api/client'
import type { HistorySession, LLMExplanation } from '../types'
import RiskAlerts from '../components/RiskAlerts'
import DiseaseResults from '../components/DiseaseResults'
import LLMExplanationPanel from '../components/LLMExplanationPanel'

export default function HistoryPage() {
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [patient, setPatient] = useState<{ code: string; name: string; dob: string } | null>(null)
  const [sessions, setSessions] = useState<HistorySession[]>([])
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  async function search(e: React.FormEvent) {
    e.preventDefault()
    if (!code.trim()) return
    setLoading(true)
    setError('')
    setDetail(null)
    try {
      const data = await getPatientHistory(code.trim())
      setPatient(data.patient)
      setSessions(data.sessions)
    } catch {
      setError('Không tìm thấy bệnh nhân hoặc lỗi kết nối')
      setPatient(null)
      setSessions([])
    } finally {
      setLoading(false)
    }
  }

  async function openSession(sessionId: number) {
    if (!patient) return
    setDetailLoading(true)
    try {
      const data = await getSessionDetail(patient.code, sessionId)
      setDetail(data)
    } catch {
      setError('Không tải được chi tiết phiên')
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Lịch sử chẩn đoán</h2>
        <p className="text-gray-500 text-sm mt-1">Tra cứu theo mã bệnh nhân (ví dụ: BN-00001)</p>
      </div>

      <form onSubmit={search} className="flex gap-2">
        <input
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Nhập mã bệnh nhân..."
        />
        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          Tìm
        </button>
      </form>

      {error && <p className="text-danger-600 text-sm">{error}</p>}

      {patient && (
        <div className="bg-white rounded-xl border p-4">
          <p className="font-semibold">{patient.name}</p>
          <p className="text-sm text-gray-500">
            Mã: {patient.code} · Sinh: {patient.dob} · {sessions.length} phiên
          </p>
        </div>
      )}

      {sessions.length > 0 && (
        <div className="bg-white rounded-xl border divide-y">
          {sessions.map((s) => (
            <button
              key={s.session_id}
              type="button"
              onClick={() => openSession(s.session_id)}
              className="w-full flex items-center justify-between p-4 hover:bg-gray-50 text-left transition-colors"
            >
              <div>
                <p className="font-medium text-gray-900">
                  #{s.session_id} — {s.top_diagnosis ?? 'Chưa có kết quả'}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {new Date(s.created_at).toLocaleString('vi-VN')} · Tuổi {s.age} ·{' '}
                  {s.risk_alert_count} cảnh báo · Model: {s.model_version}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  Triệu chứng: {s.symptoms_input?.join(', ')}
                </p>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-400 shrink-0" />
            </button>
          ))}
        </div>
      )}

      {detailLoading && (
        <div className="flex justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-primary-600" />
        </div>
      )}

      {detail && !detailLoading && (
        <div className="space-y-4 border-t pt-4">
          <h3 className="font-bold text-lg">
            Chi tiết phiên #{(detail as { session_id: number }).session_id}
          </h3>
          <RiskAlerts alerts={(detail as { risk_alerts: [] }).risk_alerts ?? []} />
          <DiseaseResults diseases={(detail as { diagnosis_results: [] }).diagnosis_results ?? []} />
          <LLMExplanationPanel
            explanation={(detail as { llm_explanation?: LLMExplanation | null }).llm_explanation}
          />
        </div>
      )}
    </div>
  )
}
