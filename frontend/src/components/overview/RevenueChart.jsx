import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend, LabelList,
} from "recharts";
import { colors, tooltipStyle, axisProps, gridProps, MultiLineTick, legendProps } from "../../chartTheme";

export default function RevenueChart({ courses }) {
  if (!courses || courses.length === 0) {
    return <p className="chart-empty">No revenue data available.</p>;
  }

  const data = courses.map((c) => {
    const rev = (c.revenue_cents || 0) / 100;
    const hasSales = rev > 0;
    return {
      name: c.product_name,
      revenue: rev,
      avgFee: hasSales && c.enrollment_count > 0 ? Math.round(rev / c.enrollment_count) : null,
    };
  });

  const hasRevenue = data.some((d) => d.revenue > 0);
  if (!hasRevenue) {
    return (
      <div className="chart-card">
        <h3>Revenue by Course</h3>
        <p className="chart-empty">No revenue data yet.</p>
      </div>
    );
  }

  const maxNameLen = Math.max(...courses.map((c) => c.product_name.length));
  const bottomMargin = Math.min(Math.ceil(maxNameLen / 18) * 14 + 10, 70);
  const hasAvgFee = data.some((d) => d.avgFee != null);

  return (
    <div className="chart-card">
      <h3>Revenue by Course</h3>
      <ResponsiveContainer width="100%" height={300 + bottomMargin}>
        <ComposedChart data={data} margin={{ top: 5, right: hasAvgFee ? 60 : 20, bottom: bottomMargin, left: 10 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="name" tick={<MultiLineTick />} interval={0} axisLine={{ stroke: "#292524" }} tickLine={false} />
          <YAxis yAxisId="revenue" {...axisProps.y} tickFormatter={(v) => `$${v.toLocaleString()}`} />
          {hasAvgFee && (
            <YAxis yAxisId="fee" orientation="right" {...axisProps.y} tickFormatter={(v) => `$${v}`} label={{ value: "Avg Fee", angle: 90, position: "insideRight", fill: "#78716c", fontSize: 11 }} />
          )}
          <Tooltip
            {...tooltipStyle}
            formatter={(val, name) => {
              if (val == null) return ["-", ""];
              const label = name === "Revenue" ? "Revenue" : "Avg Fee";
              return [`$${Math.round(val).toLocaleString()}`, label];
            }}
          />
          <Legend {...legendProps} />
          <Bar yAxisId="revenue" dataKey="revenue" fill={colors.primary} radius={[4, 4, 0, 0]} name="Revenue" />
          {hasAvgFee && (
            <Line
              yAxisId="fee"
              dataKey="avgFee"
              stroke={colors.warm}
              strokeWidth={2}
              dot={{ r: 5, fill: colors.warm }}
              connectNulls={false}
              name="Avg Fee"
            >
              <LabelList
                dataKey="avgFee"
                position="top"
                formatter={(v) => v != null ? `$${v}` : ""}
                fill="#f4a261"
                fontSize={11}
                offset={8}
              />
            </Line>
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
