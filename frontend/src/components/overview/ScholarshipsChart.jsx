import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend, LabelList,
} from "recharts";
import { colors, tooltipStyle, axisProps, gridProps, MultiLineTick, legendProps } from "../../chartTheme";

export default function ScholarshipsChart({ courses }) {
  if (!courses || courses.length === 0) {
    return <p className="chart-empty">No scholarship data available.</p>;
  }

  const data = courses.map((c) => ({
    name: c.product_name,
    count: c.scholarship_count || 0,
    amount: (c.scholarship_amount_cents || 0) / 100,
  }));

  const hasData = data.some((d) => d.count > 0);
  if (!hasData) {
    return (
      <div className="chart-card">
        <h3>Scholarships</h3>
        <p className="chart-empty">No scholarship data yet.</p>
      </div>
    );
  }

  const maxNameLen = Math.max(...courses.map((c) => c.product_name.length));
  const bottomMargin = Math.min(Math.ceil(maxNameLen / 18) * 14 + 10, 70);

  return (
    <div className="chart-card">
      <h3>Scholarships</h3>
      <ResponsiveContainer width="100%" height={300 + bottomMargin}>
        <ComposedChart data={data} margin={{ top: 5, right: 60, bottom: bottomMargin, left: 10 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="name" tick={<MultiLineTick />} interval={0} axisLine={{ stroke: "#292524" }} tickLine={false} />
          <YAxis yAxisId="count" allowDecimals={false} {...axisProps.y} />
          <YAxis yAxisId="amount" orientation="right" {...axisProps.y} tickFormatter={(v) => `$${v}`} />
          <Tooltip
            {...tooltipStyle}
            formatter={(val, name) => {
              if (name === "Scholarship $") return [`$${val.toLocaleString()}`, "Scholarship $ awarded"];
              return [val, "Scholarships"];
            }}
          />
          <Legend {...legendProps} />
          <Bar yAxisId="count" dataKey="count" fill={colors.tertiary} radius={[4, 4, 0, 0]} name="Scholarships" />
          <Line yAxisId="amount" dataKey="amount" stroke={colors.warm} strokeWidth={2} dot={{ r: 5, fill: colors.warm }} name="Scholarship $">
            <LabelList
              dataKey="amount"
              position="top"
              formatter={(v) => v != null && v > 0 ? `$${v.toLocaleString()}` : ""}
              fill="#f4a261"
              fontSize={11}
              offset={8}
            />
          </Line>
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
