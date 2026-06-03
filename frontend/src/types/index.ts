export interface VitalSigns {
  temperature?: number
  systolic_bp?: number
  diastolic_bp?: number
  heart_rate?: number
  spo2?: number
  respiratory_rate?: number
  weight?: number
  height?: number
}

export interface DiagnosisRequest {
  patient_name: string
  date_of_birth: string
  age: number
  gender: string
  province: string
  vital_signs?: VitalSigns
  symptoms: string[]
  symptom_duration_days?: number
  symptom_onset?: string
  symptom_severity?: string
  medical_history?: {
    allergies?: string[]
    chronic_conditions?: string[]
    current_medications?: string[]
    family_history?: string[]
  }
  risk_factors?: {
    smoking?: string
    alcohol?: string
    recent_contact_sick?: boolean
    recent_travel?: boolean
  }
  use_demographic_adjustment: boolean
  engine?: string
}

export interface RiskAlert {
  level: string
  message: string
  advice: string
  triggered_by: string
}

export interface DiseaseMatch {
  disease_id: number
  disease_name: string
  category: string
  severity: string
  confidence_score: number
  weighted_score: number
  ml_score: number
  matched_symptoms: { symptom_id?: number; symptom_name?: string; name?: string; weight: number }[]
  advice: string
  explanation: string
  lime_explanation?: {
    features: Array<{
      name: string
      contribution: number
    }>
    predicted_proba: number
  }
  shap_explanation?: {
    features: Array<{
      name: string
      shap_value: number
      importance: number
    }>
  }
}

export interface RagSource {
  source_id: string
  source_type: string
  title: string
  content: string
  relevance_score: number
  metadata: Record<string, unknown>
}

export interface LLMExplanation {
  enabled: boolean
  provider: string
  model?: string | null
  status: string
  summary: string
  reasoning: string[]
  safety_notes: string[]
  fairness_notes: string[]
  limitations: string[]
  suggested_next_steps: string[]
  first_aid_and_symptom_analysis?: string
  sources: RagSource[]
}

export interface DiagnosisResponse {
  session_id: number
  patient_code: string
  patient_name: string
  risk_alerts: RiskAlert[]
  bmi?: number
  vital_flags: Record<string, unknown>
  top_diseases: DiseaseMatch[]
  demographic_adjustment_applied: boolean
  demographic_adjustment_details?: Record<string, unknown>
  llm_explanation?: LLMExplanation | null
  disclaimer: string
}

export interface HistorySession {
  session_id: number
  created_at: string
  age: number
  symptoms_input: string[]
  top_diagnosis: string | null
  risk_alert_count: number
  model_version: string
}

export interface AdminStats {
  diseases: number
  symptoms: number
  patients: number
  diagnosis_sessions: number
  active_model: {
    version: string
    accuracy: number
    f1_score: number
  } | null
  total_models: number
}

export interface Disease {
  id: number
  name: string
  category: string
  severity: string
  description?: string
  advice?: string
}

export interface Symptom {
  id: number
  name: string
  slug: string
  category?: string
}

export interface MLModel {
  id: number
  version: string
  accuracy: number
  f1_score: number
  num_diseases: number
  num_symptoms: number
  training_samples: number
  is_active: boolean
  notes: string
  created_at: string
}

export interface LLMTrainingExport {
  message: string
  file_path: string
  examples: number
  format: string
  max_examples_per_disease: number
}
