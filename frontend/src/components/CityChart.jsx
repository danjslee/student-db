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
          <CartesianGrid strokeDasharray="3 3" stroke="#292524" />
          <XAxis
            dataKey="label"
            angle={-45}
            textAnchor="end"
            interval={0}
            tick={{ fontSize: 11, fill: "#a8a29e" }}
            axisLine={{ stroke: "#44403c" }}
            tickLine={{ stroke: "#44403c" }}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fill: "#a8a29e" }}
            axisLine={{ stroke: "#44403c" }}
            tickLine={{ stroke: "#44403c" }}
          />
          <Tooltip
            contentStyle={{ backgroundColor: "#292524", border: "1px solid #44403c", borderRadius: "8px", color: "#fff" }}
            labelStyle={{ color: "#d6d3d1" }}
            itemStyle={{ color: "#fff" }}
          />
          <Bar dataKey="count" fill="#059669" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
