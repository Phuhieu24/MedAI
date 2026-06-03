import { useState } from 'react'
import { Loader2, Send } from 'lucide-react'
import { runDiagnosis } from '../api/client'
import type { DiagnosisRequest, DiagnosisResponse } from '../types'
import RiskAlerts from '../components/RiskAlerts'
import DiseaseResults from '../components/DiseaseResults'
import LLMExplanationPanel from '../components/LLMExplanationPanel'
import ExplanationCard from '../components/ExplanationCard'

const GENDERS = ['Nam', 'Nữ', 'Khác']
const PROVINCES = [
  'Hà Nội', 'TP.HCM', 'Đà Nẵng', 'Hải Phòng', 'Cần Thơ',
  'An Giang', 'Bình Dương', 'Đồng Nai', 'Khánh Hòa', 'Thanh Hóa', 'Khác',
]
const ONSET = ['Đột ngột', 'Từ từ', 'Không rõ']
const SEVERITY = ['Nhẹ', 'Trung bình', 'Nặng']

function parseList(text: string): string[] {
  return text
    .split(/[,;|\n]/)
    .map((s) => s.trim())
    .filter(Boolean)
}

const emptyForm = {
  patient_name: '',
  date_of_birth: '',
  age: '', // Sẽ được tính tự động, nhưng giữ lại để compatibility
  gender: 'Nam',
  province: 'Hà Nội',
  symptoms: '',
  symptom_duration_days: '',
  symptom_onset: '',
  symptom_severity: '',
  temperature: '',
  systolic_bp: '',
  diastolic_bp: '',
  heart_rate: '',
  spo2: '',
  respiratory_rate: '',
  weight: '',
  height: '',
  allergies: '',
  chronic_conditions: '',
  smoking: '',
  alcohol: '',
  recent_contact_sick: false,
  recent_travel: false,
  use_demographic_adjustment: true,
  engine: 'xgboost',
}

export default function DiagnosisPage() {
  const [form, setForm] = useState(emptyForm)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<DiagnosisResponse | null>(null)

  const set = (key: keyof typeof form, value: string | boolean) =>
    setForm((f) => ({ ...f, [key]: value }))

  const num = (v: string) => (v === '' ? undefined : Number(v))

  const parseDDMMYYYY = (dateString: string): Date | null => {
    if (!dateString) return null
    const parts = dateString.split('/')
    if (parts.length === 3) {
      const day = parseInt(parts[0], 10)
      const month = parseInt(parts[1], 10) - 1
      const year = parseInt(parts[2], 10)
      const date = new Date(year, month, day)
      if (date.getFullYear() === year && date.getMonth() === month && date.getDate() === day) {
        return date
      }
    }
    return null
  }

  // Tính tuổi tự động từ ngày sinh
  const calculateAge = (dob: string): number => {
    const birthDate = parseDDMMYYYY(dob)
    if (!birthDate) return -1
    const today = new Date()
    let age = today.getFullYear() - birthDate.getFullYear()
    const monthDiff = today.getMonth() - birthDate.getMonth()
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--
    }
    return Math.max(0, age)
  }

  const calculatedAge = calculateAge(form.date_of_birth)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setResult(null)

    const symptoms = parseList(form.symptoms)
    if (!form.patient_name.trim()) {
      setError('Vui lòng nhập tên bệnh nhân')
      return
    }
    if (!form.date_of_birth) {
      setError('Vui lòng nhập ngày sinh')
      return
    }
    const parsedDob = parseDDMMYYYY(form.date_of_birth)
    if (!parsedDob) {
      setError('Ngày sinh không hợp lệ (Vui lòng nhập đúng định dạng dd/mm/yyyy)')
      return
    }
    if (calculatedAge < 0 || calculatedAge > 150) {
      setError('Ngày sinh không hợp lệ hoặc tuổi vượt quá giới hạn')
      return
    }
    if (symptoms.length === 0) {
      setError('Vui lòng nhập ít nhất một triệu chứng')
      return
    }

    const isoDateOfBirth = `${parsedDob.getFullYear()}-${String(parsedDob.getMonth() + 1).padStart(2, '0')}-${String(parsedDob.getDate()).padStart(2, '0')}`

    const payload: DiagnosisRequest = {
      patient_name: form.patient_name.trim(),
      date_of_birth: isoDateOfBirth,
      age: calculatedAge,
      gender: form.gender,
      province: form.province,
      symptoms,
      symptom_duration_days: num(form.symptom_duration_days),
      symptom_onset: form.symptom_onset || undefined,
      symptom_severity: form.symptom_severity || undefined,
      use_demographic_adjustment: form.use_demographic_adjustment,
      engine: form.engine,
      vital_signs: {
        temperature: num(form.temperature),
        systolic_bp: num(form.systolic_bp) as number | undefined,
        diastolic_bp: num(form.diastolic_bp) as number | undefined,
        heart_rate: num(form.heart_rate) as number | undefined,
        spo2: num(form.spo2),
        respiratory_rate: num(form.respiratory_rate) as number | undefined,
        weight: num(form.weight),
        height: num(form.height),
      },
      medical_history: {
        allergies: parseList(form.allergies),
        chronic_conditions: parseList(form.chronic_conditions),
      },
      risk_factors: {
        smoking: form.smoking || undefined,
        alcohol: form.alcohol || undefined,
        recent_contact_sick: form.recent_contact_sick,
        recent_travel: form.recent_travel,
      },
    }

    setLoading(true)
    try {
      const res = await runDiagnosis(payload)
      setResult(res)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Không thể kết nối backend. Hãy chạy server tại cổng 8000.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  const inputCls =
    'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent'
  const labelCls = 'block text-sm font-medium text-gray-700 mb-1'

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Chẩn đoán mới</h2>
        <p className="text-gray-500 text-sm mt-1">
          Nhập thông tin bệnh nhân và triệu chứng để nhận gợi ý chẩn đoán AI
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="bg-white rounded-xl border p-5 space-y-4">
          <h3 className="font-semibold text-gray-800 border-b pb-2">Thông tin bệnh nhân</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Họ tên *</label>
              <input className={inputCls} value={form.patient_name} onChange={(e) => set('patient_name', e.target.value)} placeholder="Nguyễn Văn A" />
            </div>
            <div>
              <label className={labelCls}>Ngày sinh *</label>
              <input
                type="text"
                placeholder="dd/mm/yyyy"
                className={inputCls}
                value={form.date_of_birth}
                onChange={(e) => {
                  let v = e.target.value.replace(/\D/g, '')
                  if (v.length > 8) v = v.slice(0, 8)
                  if (v.length > 4) v = `${v.slice(0, 2)}/${v.slice(2, 4)}/${v.slice(4)}`
                  else if (v.length > 2) v = `${v.slice(0, 2)}/${v.slice(2)}`
                  set('date_of_birth', v)
                }}
              />
            </div>
            <div>
              <label className={labelCls}>Tuổi (tính tự động)</label>
              <div className={`${inputCls} flex items-center bg-gray-50 cursor-not-allowed`}>
                <span className="text-lg font-semibold text-gray-700">{calculatedAge >= 0 ? calculatedAge : '--'}</span>
                <span className="ml-2 text-sm text-gray-500">tuổi</span>
              </div>
            </div>
            <div>
              <label className={labelCls}>Giới tính</label>
              <select className={inputCls} value={form.gender} onChange={(e) => set('gender', e.target.value)}>
                {GENDERS.map((g) => <option key={g}>{g}</option>)}
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className={labelCls}>Tỉnh/Thành phố</label>
              <select className={inputCls} value={form.province} onChange={(e) => set('province', e.target.value)}>
                {PROVINCES.map((p) => <option key={p}>{p}</option>)}
              </select>
            </div>
          </div>
        </section>

        <section className="bg-white rounded-xl border p-5 space-y-4">
          <h3 className="font-semibold text-gray-800 border-b pb-2">Triệu chứng *</h3>
          <div>
            <label className={labelCls}>Triệu chứng (phân cách bằng dấu phẩy)</label>
            <textarea
              className={`${inputCls} min-h-[80px]`}
              value={form.symptoms}
              onChange={(e) => set('symptoms', e.target.value)}
              placeholder="sốt, ho, đau đầu, mệt mỏi..."
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className={labelCls}>Số ngày</label>
              <input type="number" className={inputCls} value={form.symptom_duration_days} onChange={(e) => set('symptom_duration_days', e.target.value)} min={0} />
            </div>
            <div>
              <label className={labelCls}>Khởi phát</label>
              <select className={inputCls} value={form.symptom_onset} onChange={(e) => set('symptom_onset', e.target.value)}>
                <option value="">—</option>
                {ONSET.map((o) => <option key={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Mức độ</label>
              <select className={inputCls} value={form.symptom_severity} onChange={(e) => set('symptom_severity', e.target.value)}>
                <option value="">—</option>
                {SEVERITY.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
          </div>
        </section>

        <section className="bg-white rounded-xl border p-5 space-y-4">
          <h3 className="font-semibold text-gray-800 border-b pb-2">Sinh hiệu (tuỳ chọn)</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              ['Nhiệt độ (°C)', 'temperature'],
              ['Huyết áp tâm thu', 'systolic_bp'],
              ['Huyết áp tâm trương', 'diastolic_bp'],
              ['Nhịp tim', 'heart_rate'],
              ['SpO2 (%)', 'spo2'],
              ['Nhịp thở', 'respiratory_rate'],
              ['Cân nặng (kg)', 'weight'],
              ['Chiều cao (cm)', 'height'],
            ].map(([label, key]) => (
              <div key={key}>
                <label className={labelCls}>{label}</label>
                <input
                  type="number"
                  step="any"
                  className={inputCls}
                  value={form[key as keyof typeof form] as string}
                  onChange={(e) => set(key as keyof typeof form, e.target.value)}
                />
              </div>
            ))}
          </div>
        </section>

        <section className="bg-white rounded-xl border p-5 space-y-4">
          <h3 className="font-semibold text-gray-800 border-b pb-2">Tiền sử & yếu tố nguy cơ</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Dị ứng</label>
              <input className={inputCls} value={form.allergies} onChange={(e) => set('allergies', e.target.value)} placeholder="penicillin, hải sản..." />
            </div>
            <div>
              <label className={labelCls}>Bệnh mạn tính</label>
              <input className={inputCls} value={form.chronic_conditions} onChange={(e) => set('chronic_conditions', e.target.value)} placeholder="tiểu đường, cao huyết áp..." />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.use_demographic_adjustment}
              onChange={(e) => set('use_demographic_adjustment', e.target.checked)}
              className="rounded"
            />
            Áp dụng điều chỉnh nhân khẩu học (công bằng thuật toán)
          </label>

        </section>

        {error && (
          <div className="bg-danger-50 border border-danger-500 text-danger-600 rounded-lg p-3 text-sm">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="flex items-center justify-center gap-2 w-full sm:w-auto px-6 py-3 bg-primary-600 text-white rounded-xl font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
          {loading ? 'Đang phân tích...' : 'Chạy chẩn đoán'}
        </button>
      </form>

      {result && (
        <div className="space-y-4 border-t pt-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-xl font-bold text-gray-900">Kết quả chẩn đoán</h3>
            <span className="text-sm bg-gray-100 px-3 py-1 rounded-full">
              Mã BN: <strong>{result.patient_code}</strong> · Phiên #{result.session_id}
            </span>
          </div>

          {result.bmi != null && (
            <p className="text-sm text-gray-600">BMI: <strong>{result.bmi.toFixed(1)}</strong></p>
          )}

          <RiskAlerts alerts={result.risk_alerts} />
          <DiseaseResults diseases={result.top_diseases} />
          {result.top_diseases?.[0]?.lime_explanation && (
            <ExplanationCard
              limeFeatures={result.top_diseases[0].lime_explanation.features}
              shapFeatures={result.top_diseases[0].shap_explanation?.features || []}
              predictedClass={result.top_diseases[0].disease_name}
              predictedProba={result.top_diseases[0].lime_explanation.predicted_proba}
            />
          )}
          <LLMExplanationPanel explanation={result.llm_explanation} />

          {result.demographic_adjustment_applied && result.demographic_adjustment_details && (
            <p className="text-xs text-gray-500 bg-gray-50 rounded-lg p-2">
              Điều chỉnh nhân khẩu học đã được áp dụng để đảm bảo công bằng thuật toán.
            </p>
          )}

          <p className="text-xs text-gray-400 italic border-t pt-3">{result.disclaimer}</p>
        </div>
      )}
    </div>
  )
}
