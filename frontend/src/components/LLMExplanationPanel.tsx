import {
  Brain,
  FileText,
  ListChecks,
  Scale,
  ShieldCheck,
  TriangleAlert,
  Stethoscope,
  type LucideIcon,
} from 'lucide-react'
import type { LLMExplanation } from '../types'

function statusLabel(status: string) {
  if (status === 'llm_generated') return 'LLM'
  if (status.includes('missing')) return 'RAG fallback'
  if (status.includes('error')) return 'RAG fallback'
  return 'Structured RAG'
}

function NoteList({
  title,
  items,
  icon: Icon,
}: {
  title: string
  items: string[]
  icon: LucideIcon
}) {
  if (!items.length) return null
  return (
    <div className="border border-gray-200 rounded-lg p-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
        <Icon className="w-4 h-4 text-primary-600" />
        {title}
      </div>
      <ul className="mt-2 space-y-1 text-sm text-gray-600">
        {items.map((item, index) => (
          <li key={index} className="leading-5">
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function LLMExplanationPanel({
  explanation,
}: {
  explanation?: LLMExplanation | null
}) {
  if (!explanation) return null

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary-50 flex items-center justify-center">
            <Brain className="w-5 h-5 text-primary-700" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Giải thích RAG/LLM</h3>
            <p className="text-xs text-gray-500">
              {explanation.provider}
              {explanation.model ? ` · ${explanation.model}` : ''}
            </p>
          </div>
        </div>
        <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 text-gray-700">
          {statusLabel(explanation.status)}
        </span>
      </div>

      <p className="text-sm text-gray-700 leading-6">{explanation.summary}</p>

      {explanation.first_aid_and_symptom_analysis && (
        <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4 my-4">
          <div className="flex items-center gap-2 font-bold text-indigo-900 mb-2">
            <Stethoscope className="w-5 h-5" />
            AI Phân Tích & Sơ Cứu
          </div>
          <p className="text-sm text-indigo-800 leading-relaxed">
            {explanation.first_aid_and_symptom_analysis}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <NoteList title="Độ tin cậy" items={explanation.reasoning} icon={ListChecks} />
        <NoteList title="An toàn, chịu lỗi" items={explanation.safety_notes} icon={ShieldCheck} />
        <NoteList title="Công bằng và nhóm yếu thế" items={explanation.fairness_notes} icon={Scale} />
        <NoteList title="Giới hạn cần biết" items={explanation.limitations} icon={TriangleAlert} />
      </div>

      {explanation.suggested_next_steps.length > 0 && (
        <div className="border border-gray-200 rounded-lg p-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
            <ListChecks className="w-4 h-4 text-primary-600" />
            Bước tiếp theo
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {explanation.suggested_next_steps.map((step, index) => (
              <span key={index} className="text-xs bg-success-50 text-success-700 px-2 py-1 rounded-full">
                {step}
              </span>
            ))}
          </div>
        </div>
      )}

      {explanation.sources.length > 0 && (
        <div className="border-t pt-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
            <FileText className="w-4 h-4 text-primary-600" />
            Nguồn RAG đã truy xuất
          </div>
          <div className="mt-2 space-y-2">
            {explanation.sources.slice(0, 6).map((source) => (
              <details key={source.source_id} className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
                <summary className="cursor-pointer text-sm font-medium text-gray-800">
                  {source.title}
                  <span className="ml-2 text-xs text-gray-400">
                    {source.source_type} · {(source.relevance_score * 100).toFixed(0)}%
                  </span>
                </summary>
                <p className="mt-2 text-xs text-gray-600 leading-5">{source.content}</p>
              </details>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
