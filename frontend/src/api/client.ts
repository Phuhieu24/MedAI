import axios from 'axios'
import type {
  DiagnosisRequest,
  DiagnosisResponse,
  AdminStats,
  Disease,
  LLMTrainingExport,
  Symptom,
  MLModel,
} from '../types'

const api = axios.create({ baseURL: '/api' })

export async function runDiagnosis(data: DiagnosisRequest): Promise<DiagnosisResponse> {
  const res = await api.post<DiagnosisResponse>('/diagnosis', data)
  return res.data
}

export async function getPatientHistory(patientCode: string) {
  const res = await api.get(`/diagnosis/history/${patientCode}`)
  return res.data
}

export async function getSessionDetail(patientCode: string, sessionId: number) {
  const res = await api.get(`/diagnosis/history/${patientCode}/session/${sessionId}`)
  return res.data
}

export async function getStats(): Promise<AdminStats> {
  const res = await api.get<AdminStats>('/admin/stats')
  return res.data
}

export async function listDiseases(): Promise<Disease[]> {
  const res = await api.get<Disease[]>('/admin/diseases', { params: { limit: 500 } })
  return res.data
}

export async function listSymptoms(): Promise<Symptom[]> {
  const res = await api.get<Symptom[]>('/admin/symptoms', { params: { limit: 500 } })
  return res.data
}

export async function listModels(): Promise<MLModel[]> {
  const res = await api.get<MLModel[]>('/admin/models')
  return res.data
}

export async function activateModel(modelId: number) {
  const res = await api.post(`/admin/models/${modelId}/activate`)
  return res.data
}

export async function triggerXGBoostTraining(notes = '') {
  const res = await api.post('/admin/train-xgboost', null, { params: { notes } })
  return res.data
}

export async function checkOllamaStatus() {
  const res = await api.get('/admin/ollama/status')
  return res.data
}

export async function rebuildVectorDB() {
  const res = await api.post('/admin/vector-db/index')
  return res.data
}

export async function llmImportDataset(file: File) {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post('/admin/llm-ingest-file', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function importPatientsCSV(file: File) {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post('/admin/import-patients-csv', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function listPatients(name?: string) {
  const res = await api.get('/admin/patients', { params: { name, limit: 50 } })
  return res.data
}

export async function healthCheck() {
  const res = await axios.get('/health')
  return res.data
}
