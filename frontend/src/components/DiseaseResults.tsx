import type { DiseaseMatch } from '../types'

function confidenceColor(score: number) {
  if (score >= 0.7) return 'bg-success-500'
  if (score >= 0.4) return 'bg-warning-500'
  return 'bg-gray-400'
}

export default function DiseaseResults({ diseases }: { diseases: DiseaseMatch[] }) {
  if (!diseases.length) {
    return (
      <p className="text-gray-500 text-center py-6">
        Không tìm thấy bệnh phù hợp. Vui lòng nhập thêm triệu chứng hoặc kiểm tra dữ liệu hệ thống.
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-gray-800">Top bệnh gợi ý</h3>
      {diseases.map((d, i) => (
        <div key={d.disease_id} className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <span className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-100 text-primary-700 font-bold text-sm">
                {i + 1}
              </span>
              <div>
                <h4 className="font-semibold text-gray-900">{d.disease_name}</h4>
                <p className="text-xs text-gray-500">
                  {d.category} · Mức độ: {d.severity}
                </p>
              </div>
            </div>
            <div className="text-right shrink-0">
              <span className="text-2xl font-bold text-primary-700">
                {(d.confidence_score * 100).toFixed(0)}%
              </span>
              <p className="text-xs text-gray-400">độ tin cậy</p>
            </div>
          </div>

          <div className="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${confidenceColor(d.confidence_score)}`}
              style={{ width: `${Math.min(d.confidence_score * 100, 100)}%` }}
            />
          </div>

          <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-500">
            <span>Điểm triệu chứng: {(d.weighted_score * 100).toFixed(0)}%</span>
            <span>Điểm ML: {(d.ml_score * 100).toFixed(0)}%</span>
          </div>

          {d.matched_symptoms?.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {d.matched_symptoms.map((s, j) => (
                <span
                  key={j}
                  className="text-xs bg-primary-50 text-primary-700 px-2 py-0.5 rounded-full"
                >
                  {s.symptom_name ?? s.name}
                </span>
              ))}
            </div>
          )}

          {d.advice && (
            <p className="mt-2 text-sm text-success-700 bg-success-50 rounded-lg p-2">
              💡 {d.advice}
            </p>
          )}

          {d.explanation && (
            <p className="mt-1 text-xs text-gray-500 italic">{d.explanation}</p>
          )}

          {d.lime_explanation && (
            <div className="mt-3 bg-blue-50 border border-blue-200 rounded-lg p-2">
              <p className="text-xs font-medium text-blue-900 mb-1">📊 LIME Explanation</p>
              <div className="space-y-1 text-xs text-blue-800">
                {d.lime_explanation.features?.slice(0, 3).map((f, j) => (
                  <div key={j} className="flex justify-between">
                    <span>{f.name}</span>
                    <span className="font-mono">{(f.contribution * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {d.shap_explanation && (
            <div className="mt-2 bg-purple-50 border border-purple-200 rounded-lg p-2">
              <p className="text-xs font-medium text-purple-900 mb-1">📈 SHAP Importance</p>
              <div className="space-y-1 text-xs text-purple-800">
                {d.shap_explanation.features?.slice(0, 3).map((f, j) => (
                  <div key={j} className="flex justify-between">
                    <span>{f.name}</span>
                    <span className="font-mono">{(f.importance * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
