import { useEffect, useState } from 'react'
import {
  Database, Upload, Brain, Users, RefreshCw, Loader2, CheckCircle, FileText, Zap, Network, Box,
} from 'lucide-react'
import {
  getStats, listDiseases, listSymptoms, listModels,
  activateModel, llmImportDataset, importPatientsCSV, listPatients,
  triggerXGBoostTraining, checkOllamaStatus, rebuildVectorDB,
} from '../api/client'
import type { AdminStats, Disease, Symptom, MLModel } from '../types'

type Tab = 'dashboard' | 'data' | 'models' | 'patients'

export default function AdminPage() {
  const [tab, setTab] = useState<Tab>('dashboard')
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [diseases, setDiseases] = useState<Disease[]>([])
  const [symptoms, setSymptoms] = useState<Symptom[]>([])
  const [models, setModels] = useState<MLModel[]>([])
  const [patients, setPatients] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function loadAll() {
    setLoading(true)
    setError('')
    try {
      const [s, d, sy, m, p] = await Promise.all([
        getStats(),
        listDiseases(),
        listSymptoms(),
        listModels(),
        listPatients(),
      ])
      setStats(s)
      setDiseases(d)
      setSymptoms(sy)
      setModels(m)
      setPatients(p)
    } catch {
      setError('Không kết nối được backend. Chạy: uvicorn main:app --reload (cổng 8000)')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAll()
  }, [])

  async function handleLLMImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setMessage('')
    setLoading(true)
    try {
      const res = await llmImportDataset(file)
      setMessage(`LLM Import thành công. ${res.message} ${res.errors?.length > 0 ? `Có ${res.errors.length} lỗi.` : ''}`)
      await loadAll()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Lỗi import file qua LLM')
    } finally {
      setLoading(false)
      e.target.value = ''
    }
  }

  async function handlePatientCSVImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setMessage('')
    setLoading(true)
    try {
      const res = await importPatientsCSV(file)
      setMessage(`Import ca bệnh thành công. ${res.message} ${res.errors?.length > 0 ? `Có ${res.errors.length} lỗi.` : ''}`)
      await loadAll()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Lỗi import file dữ liệu bệnh nhân')
    } finally {
      setLoading(false)
      e.target.value = ''
    }
  }

  async function handleTrainXGBoost() {
    setLoading(true)
    setMessage('')
    setError('')
    try {
      const res = await triggerXGBoostTraining('Huấn luyện XGBoost từ giao diện')
      setMessage(`XGBoost huấn luyện xong — phiên bản ${res.version ?? ''}, accuracy ${((res.accuracy ?? 0) * 100).toFixed(1)}%`)
      await loadAll()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Lỗi huấn luyện XGBoost')
    } finally {
      setLoading(false)
    }
  }

  async function handleCheckOllama() {
    setLoading(true)
    setMessage('')
    setError('')
    try {
      const res = await checkOllamaStatus()
      setMessage(`Ollama: ${res.status === 'running' ? '✓ Đang chạy' : '✗ Không hoạt động'} (Model: ${res.model || 'Chưa cấu hình'})`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Không thể kiểm tra Ollama')
    } finally {
      setLoading(false)
    }
  }

  async function handleRebuildVectorDB() {
    setLoading(true)
    setMessage('')
    setError('')
    try {
      const res = await rebuildVectorDB()
      setMessage(`Vector DB: Đã index ${res.indexed ?? 0} tài liệu thành công`)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Không thể xây dựng lại Vector DB')
    } finally {
      setLoading(false)
    }
  }

  async function handleActivate(id: number) {
    setLoading(true)
    try {
      await activateModel(id)
      setMessage('Đã kích hoạt model')
      await loadAll()
    } catch {
      setError('Không thể kích hoạt model')
    } finally {
      setLoading(false)
    }
  }

  const tabs: { id: Tab; label: string; icon: typeof Database }[] = [
    { id: 'dashboard', label: 'Tổng quan', icon: Database },
    { id: 'data', label: 'Dữ liệu', icon: Upload },
    { id: 'models', label: 'ML Models', icon: Brain },
    { id: 'patients', label: 'Bệnh nhân', icon: Users },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Quản trị hệ thống</h2>
          <p className="text-gray-500 text-sm">Quản lý dữ liệu, model ML và bệnh nhân</p>
        </div>
        <button
          type="button"
          onClick={loadAll}
          disabled={loading}
          className="flex items-center gap-1 px-3 py-2 text-sm border rounded-lg hover:bg-gray-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Làm mới
        </button>
      </div>

      {message && (
        <div className="flex items-center gap-2 bg-success-50 text-success-700 rounded-lg p-3 text-sm break-words">
          <CheckCircle className="w-4 h-4" /> {message}
        </div>
      )}
      {error && <p className="text-danger-600 text-sm bg-danger-50 rounded-lg p-3">{error}</p>}

      <div className="flex gap-1 border-b">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === id
                ? 'border-primary-600 text-primary-700'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {loading && !stats && (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
        </div>
      )}

      {tab === 'dashboard' && stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {[
            ['Bệnh', stats.diseases, 'text-primary-700'],
            ['Triệu chứng', stats.symptoms, 'text-primary-700'],
            ['Bệnh nhân', stats.patients, 'text-success-600'],
            ['Phiên chẩn đoán', stats.diagnosis_sessions, 'text-warning-600'],
            ['ML Models', stats.total_models, 'text-gray-700'],
          ].map(([label, value, color]) => (
            <div key={label as string} className="bg-white rounded-xl border p-5 text-center">
              <p className={`text-3xl font-bold ${color}`}>{value as number}</p>
              <p className="text-sm text-gray-500 mt-1">{label as string}</p>
            </div>
          ))}
          <div className="bg-white rounded-xl border p-5 col-span-2 sm:col-span-1">
            <p className="text-sm text-gray-500">Model đang dùng</p>
            <p className="font-bold text-primary-700 mt-1">
              {stats.active_model?.version ?? 'Chưa có (weighted only)'}
            </p>
            {stats.active_model && (
              <p className="text-xs text-gray-400 mt-1">
                Accuracy: {((stats.active_model.accuracy ?? 0) * 100).toFixed(1)}%
              </p>
            )}
          </div>
        </div>
      )}

      {tab === 'data' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border p-5">
            <h3 className="font-semibold mb-3">Import dữ liệu</h3>
            <p className="text-sm text-gray-500 mb-3">
              Hỗ trợ file Excel định dạng MedAI (.xlsx) hoặc CSV Kaggle (.csv)
            </p>

            <div className="flex gap-4">
              <label className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg cursor-pointer hover:bg-indigo-700 text-sm">
                <Brain className="w-4 h-4" />
                Import qua LLM (Dịch tự động)
                <input type="file" accept=".xlsx,.xls,.csv" className="hidden" onChange={handleLLMImport} />
              </label>

              <label className="inline-flex items-center gap-2 px-4 py-2 bg-success-600 text-white rounded-lg cursor-pointer hover:bg-success-700 text-sm">
                <Database className="w-4 h-4" />
                Import Patient Cases (VectorDB)
                <input type="file" accept=".csv,.xlsx" className="hidden" onChange={handlePatientCSVImport} />
              </label>
            </div>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border p-4 max-h-64 overflow-y-auto">
              <h4 className="font-medium mb-2">Bệnh ({diseases.length})</h4>
              <ul className="text-sm space-y-1">
                {diseases.slice(0, 50).map((d) => (
                  <li key={d.id} className="text-gray-700">
                    {d.name} <span className="text-gray-400">({d.category})</span>
                  </li>
                ))}
                {diseases.length > 50 && <li className="text-gray-400">...và {diseases.length - 50} bệnh khác</li>}
              </ul>
            </div>
            <div className="bg-white rounded-xl border p-4 max-h-64 overflow-y-auto">
              <h4 className="font-medium mb-2">Triệu chứng ({symptoms.length})</h4>
              <ul className="text-sm space-y-1">
                {symptoms.slice(0, 50).map((s) => (
                  <li key={s.id} className="text-gray-700">{s.name}</li>
                ))}
                {symptoms.length > 50 && <li className="text-gray-400">...và {symptoms.length - 50} triệu chứng khác</li>}
              </ul>
            </div>
          </div>
        </div>
      )}

      {tab === 'models' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">

            <button
              type="button"
              onClick={handleTrainXGBoost}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-success-600 text-white rounded-lg hover:bg-success-700 disabled:opacity-50 text-sm"
            >
              <Zap className="w-4 h-4" />
              Huấn luyện XGBoost
            </button>
            <button
              type="button"
              onClick={handleCheckOllama}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 border border-warning-200 text-warning-700 rounded-lg hover:bg-warning-50 disabled:opacity-50 text-sm"
            >
              <Network className="w-4 h-4" />
              Kiểm tra Ollama
            </button>
            <button
              type="button"
              onClick={handleRebuildVectorDB}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 border border-info-200 text-info-700 rounded-lg hover:bg-info-50 disabled:opacity-50 text-sm"
            >
              <Box className="w-4 h-4" />
              Xây dựng Vector DB
            </button>

          </div>
          <div className="bg-white rounded-xl border divide-y">
            {models.length === 0 && (
              <p className="p-4 text-gray-500 text-sm">Chưa có model. Import dữ liệu rồi huấn luyện.</p>
            )}
            {models.map((m) => (
              <div key={m.id} className="flex items-center justify-between p-4">
                <div>
                  <p className="font-medium">
                    {m.version}
                    {m.is_active && (
                      <span className="ml-2 text-xs bg-success-100 text-success-700 px-2 py-0.5 rounded-full">
                        Đang dùng
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-gray-500">
                    Accuracy {(m.accuracy * 100).toFixed(1)}% · F1 {(m.f1_score * 100).toFixed(1)}% ·{' '}
                    {m.training_samples} mẫu · {new Date(m.created_at).toLocaleDateString('vi-VN')}
                  </p>
                </div>
                {!m.is_active && (
                  <button
                    type="button"
                    onClick={() => handleActivate(m.id)}
                    disabled={loading}
                    className="text-sm text-primary-600 hover:underline"
                  >
                    Kích hoạt
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'patients' && (
        <div className="bg-white rounded-xl border divide-y">
          {patients.length === 0 && (
            <p className="p-4 text-gray-500 text-sm">Chưa có bệnh nhân nào.</p>
          )}
          {patients.map((p) => (
            <div key={p.patient_code as string} className="p-4 flex justify-between">
              <div>
                <p className="font-medium">{p.name as string}</p>
                <p className="text-xs text-gray-500">
                  {p.patient_code as string} · Sinh {p.date_of_birth as string}
                </p>
              </div>
              <span className="text-sm text-gray-400">{p.session_count as number} phiên</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
