import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { colors, tooltipStyle, axisProps, gridProps } from "../chartTheme";

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
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="label" angle={-45} textAnchor="end" interval={0} {...axisProps.x} />
          <YAxis allowDecimals={false} {...axisProps.y} />
          <Tooltip {...tooltipStyle} />
          <Bar dataKey="count" fill={colors.secondary} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
