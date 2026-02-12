import { useState, useEffect } from "react";
import { fetchSurveyResponseRates } from "../../api";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { colors } from "../../chartTheme";

function RadialGauge({ value, label, color = colors.primary }) {
  const pct = Math.round(value * 100);
  const data = [
    { value: pct },
    { value: 100 - pct },
  ];

  return (
    <div className="gauge-wrapper">
      <ResponsiveContainer width={140} height={140}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            cx="50%"
            cy="50%"
            startAngle={90}
            endAngle={-270}
            innerRadius="70%"
            outerRadius="90%"
            paddingAngle={0}
            stroke="none"
          >
            <Cell fill={color} />
            <Cell fill="#292524" />
          </Pie>
          <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
            fill="#fff" fontSize={22} fontWeight={700}>
            {pct}%
          </text>
        </PieChart>
      </ResponsiveContainer>
      <div className="gauge-label">{label}</div>
    </div>
  );
}

export default function SurveyResponse({ productIds }) {
  const [rates, setRates] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchSurveyResponseRates(productIds)
      .then(setRates)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [productIds]);

  if (loading) {
    return (
      <div className="chart-card skeleton-card">
        <div className="skeleton-bar" style={{ width: "40%", height: 16, marginBottom: 16 }} />
        <div className="skeleton-bar" style={{ width: "100%", height: 140 }} />
      </div>
    );
  }

  if (!rates) return <p className="chart-empty">No survey data.</p>;

  return (
    <div className="chart-card">
      <h3>Survey Response Rates</h3>
      <div className="gauge-row">
        <RadialGauge
          value={rates.onboarding_rate || 0}
          label="Onboarding Survey"
          color={colors.primary}
        />
        <RadialGauge
          value={rates.completion_rate || 0}
          label="Completion Survey"
          color={colors.secondary}
        />
      </div>
    </div>
  );
}
