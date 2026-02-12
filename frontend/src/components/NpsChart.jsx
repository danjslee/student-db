import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell,
} from "recharts";
import { npsColor, tooltipStyle, axisProps, gridProps } from "../chartTheme";

export default function NpsChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="chart-empty">No NPS data available.</p>;
  }

  return (
    <div className="chart-card">
      <h3>NPS Score Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 5, right: 20, bottom: 60, left: 10 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="label" angle={-45} textAnchor="end" interval={0} {...axisProps.x} />
          <YAxis allowDecimals={false} {...axisProps.y} />
          <Tooltip {...tooltipStyle} />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={npsColor(parseInt(entry.label) || 0)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
