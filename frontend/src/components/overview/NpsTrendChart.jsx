import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine,
} from "recharts";
import { colors, tooltipStyle, axisProps, gridProps, MultiLineTick } from "../../chartTheme";

export default function NpsTrendChart({ courses }) {
  if (!courses || courses.length === 0) {
    return <p className="chart-empty">No NPS data available.</p>;
  }

  const data = courses
    .filter((c) => c.nps != null)
    .map((c) => ({
      name: c.product_name,
      nps: c.nps,
    }));

  if (data.length === 0) {
    return (
      <div className="chart-card">
        <h3>NPS Trend</h3>
        <p className="chart-empty">No NPS data yet.</p>
      </div>
    );
  }

  const maxNameLen = Math.max(...data.map((d) => d.name.length));
  const bottomMargin = Math.min(Math.ceil(maxNameLen / 18) * 14 + 10, 70);

  return (
    <div className="chart-card">
      <h3>NPS Trend</h3>
      <ResponsiveContainer width="100%" height={300 + bottomMargin}>
        <LineChart data={data} margin={{ top: 5, right: 20, bottom: bottomMargin, left: 10 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="name" tick={<MultiLineTick />} interval={0} axisLine={{ stroke: "#292524" }} tickLine={false} />
          <YAxis domain={[-100, 100]} {...axisProps.y} />
          <Tooltip {...tooltipStyle} />
          <ReferenceLine y={0} stroke="#78716c" strokeDasharray="3 3" />
          <ReferenceLine y={50} stroke={colors.secondary} strokeDasharray="3 3" label={{ value: "Great", fill: "#78716c", fontSize: 11 }} />
          <ReferenceLine y={-50} stroke={colors.rose} strokeDasharray="3 3" label={{ value: "Poor", fill: "#78716c", fontSize: 11 }} />
          <Line
            dataKey="nps"
            stroke={colors.primary}
            strokeWidth={2}
            dot={{ r: 5, fill: colors.primary, strokeWidth: 0 }}
            activeDot={{ r: 7, fill: colors.primary }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
