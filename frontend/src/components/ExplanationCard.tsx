import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface LimeFeature {
  name: string;
  contribution: number;
}

interface ShapFeature {
  name: string;
  shap_value: number;
  importance: number;
}

interface ExplanationCardProps {
  limeFeatures?: LimeFeature[];
  shapFeatures?: ShapFeature[];
  predictedClass?: string;
  predictedProba?: number;
}

export const ExplanationCard: React.FC<ExplanationCardProps> = ({
  limeFeatures = [],
  shapFeatures = [],
  predictedClass,
  predictedProba,
}) => {
  // Prepare data for charts
  const limeChartData = limeFeatures.map(f => ({
    name: f.name.replace(/^symptom_/, ''),
    contribution: Math.abs(f.contribution),
  }));

  const shapChartData = shapFeatures.map(f => ({
    name: f.name.replace(/^symptom_/, ''),
    importance: f.importance,
  }));

  return (
    <div className="mt-8 bg-white rounded-lg shadow p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">📊 Giải thích Dự đoán</h2>

      {predictedClass && (
        <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <p className="text-sm font-medium text-gray-700">Bệnh Dự đoán</p>
          <p className="text-xl font-bold text-blue-600">{predictedClass}</p>
          {predictedProba !== undefined && (
            <p className="text-sm text-gray-600 mt-1">
              Độ tin cậy: {(predictedProba * 100).toFixed(1)}%
            </p>
          )}
        </div>
      )}

      {/* LIME Explanation */}
      {limeChartData.length > 0 && (
        <div className="mb-8">
          <h3 className="text-lg font-semibold mb-4 text-gray-700">LIME - Giải thích Cục bộ</h3>
          <p className="text-sm text-gray-600 mb-4">
            Các triệu chứng có ảnh hưởng lớn nhất đến dự đoán này
          </p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={limeChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="name" 
                angle={-45} 
                textAnchor="end" 
                height={80}
                interval={0}
              />
              <YAxis label={{ value: 'Mức độ ảnh hưởng', angle: -90, position: 'insideLeft' }} />
              <Tooltip formatter={(value) => value.toFixed(3)} />
              <Bar dataKey="contribution" fill="#3B82F6" name="Mức độ ảnh hưởng" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* SHAP Explanation */}
      {shapChartData.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold mb-4 text-gray-700">SHAP - Phân tích Toàn cục</h3>
          <p className="text-sm text-gray-600 mb-4">
            Tầm quan trọng của các triệu chứng dựa trên toàn bộ mô hình
          </p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={shapChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="name" 
                angle={-45} 
                textAnchor="end" 
                height={80}
                interval={0}
              />
              <YAxis label={{ value: 'SHAP Value', angle: -90, position: 'insideLeft' }} />
              <Tooltip formatter={(value) => value.toFixed(4)} />
              <Bar dataKey="importance" fill="#10B981" name="Tầm quan trọng SHAP" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {limeChartData.length === 0 && shapChartData.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>Chưa có dữ liệu giải thích</p>
        </div>
      )}

      {/* Information Footer */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          💡 <strong>LIME</strong> giải thích tại sao mô hình đưa ra dự đoán này cụ thể.
          <br />
          💡 <strong>SHAP</strong> cho thấy tầm quan trọng của mỗi triệu chứng trên toàn bộ mô hình.
        </p>
      </div>
    </div>
  );
};

export default ExplanationCard;
