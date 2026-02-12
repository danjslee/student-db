import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend,
} from "recharts";
import { statusColors, tooltipStyle, axisProps, gridProps, MultiLineTick, legendProps } from "../../chartTheme";

const STATUS_ORDER = ["Full Fee", "Early Bird", "Scholarship", "Free Place", "Deferred", "Refunded"];

export default function EnrollmentsChart({ courses }) {
  if (!courses || courses.length === 0) {
    return <p className="chart-empty">No enrollment data available.</p>;
  }

  const data = courses.map((c) => ({
    name: c.product_name,
    ...(c.enrollment_breakdown || {}),
  }));

  const allStatuses = new Set();
  data.forEach((d) => {
    Object.keys(d).forEach((k) => { if (k !== "name") allStatuses.add(k); });
  });
  const statusList = STATUS_ORDER.filter((s) => allStatuses.has(s));

  if (statusList.length === 0) {
    return (
      <div className="chart-card">
        <h3>Enrollments by Course</h3>
        <p className="chart-empty">No enrollment breakdown data.</p>
      </div>
    );
  }

  const maxNameLen = Math.max(...courses.map((c) => c.product_name.length));
  const bottomMargin = Math.min(Math.ceil(maxNameLen / 18) * 14 + 10, 70);

  return (
    <div className="chart-card">
      <h3>Enrollments by Course</h3>
      <ResponsiveContainer width="100%" height={300 + bottomMargin}>
        <BarChart data={data} margin={{ top: 30, right: 20, bottom: bottomMargin, left: 10 }}>
          <CartesianGrid {...gridProps} />
          <XAxis dataKey="name" tick={<MultiLineTick />} interval={0} axisLine={{ stroke: "#292524" }} tickLine={false} />
          <YAxis allowDecimals={false} {...axisProps.y} />
          <Tooltip {...tooltipStyle} />
          <Legend {...legendProps} />
          {statusList.map((status, i) => (
            <Bar
              key={status}
              dataKey={status}
              stackId="enrollments"
              fill={statusColors[status] || "#90a4ae"}
              radius={i === statusList.length - 1 ? [4, 4, 0, 0] : 0}
              name={status}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
