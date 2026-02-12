import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { seriesPalette, tooltipStyle } from "../../chartTheme";

export default function DonutChart({ data, height = 250 }) {
  if (!data || data.length === 0) {
    return <p className="chart-empty">No data available.</p>;
  }

  const total = data.reduce((sum, d) => sum + d.count, 0);

  return (
    <div className="donut-wrapper">
      <ResponsiveContainer width="60%" height={height}>
        <PieChart>
          <Pie
            data={data}
            dataKey="count"
            nameKey="label"
            cx="50%"
            cy="50%"
            innerRadius="55%"
            outerRadius="85%"
            paddingAngle={2}
            stroke="none"
          >
            {data.map((_, i) => (
              <Cell key={i} fill={seriesPalette[i % seriesPalette.length]} />
            ))}
          </Pie>
          <Tooltip
            {...tooltipStyle}
            formatter={(val) => [`${val} (${Math.round((val / total) * 100)}%)`, ""]}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="donut-legend">
        {data.map((item, i) => (
          <div key={i} className="donut-legend-item">
            <span className="donut-legend-dot" style={{ backgroundColor: seriesPalette[i % seriesPalette.length] }} />
            <span>
              {item.label} — {Math.round((item.count / total) * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
