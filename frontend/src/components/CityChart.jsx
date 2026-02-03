import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

export default function CityChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="chart-empty">No city data available.</p>;
  }

  const top20 = data.slice(0, 20);

  return (
    <div className="chart-card">
      <h3>Students by City (Top 20)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={top20} margin={{ top: 5, right: 20, bottom: 60, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="label"
            angle={-45}
            textAnchor="end"
            interval={0}
            tick={{ fontSize: 11 }}
          />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="count" fill="#10b981" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
