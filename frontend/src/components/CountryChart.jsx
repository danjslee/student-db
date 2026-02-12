import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { colors, tooltipStyle, axisProps, gridProps } from "../chartTheme";

export default function CountryChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="chart-empty">No country data available.</p>;
  }

  return (
    <div className="chart-card">
      <h3>Students by Country</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 5, right: 20, bottom: 60, left: 10 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="label" angle={-45} textAnchor="end" interval={0} {...axisProps.x} />
          <YAxis allowDecimals={false} {...axisProps.y} />
          <Tooltip {...tooltipStyle} />
          <Bar dataKey="count" fill={colors.primary} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
