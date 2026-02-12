import { formatCurrency, colors } from "../../chartTheme";

export default function KpiCards({ data }) {
  if (!data) return null;

  const totalStudents = data.total_students || 0;
  const totalRevenue = data.total_revenue_cents || 0;
  const nps = data.nps;
  const npsColor = nps == null ? "#78716c" : nps >= 50 ? colors.secondary : nps >= 0 ? colors.warm : colors.rose;

  return (
    <div className="kpi-row" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
      <div className="kpi-card">
        <div className="kpi-label">Total Students</div>
        <div className="kpi-value">{totalStudents.toLocaleString()}</div>
        <div className="kpi-sub">{data.courses?.length || 0} courses</div>
      </div>
      <div className="kpi-card">
        <div className="kpi-label">Total Revenue</div>
        <div className="kpi-value">{formatCurrency(totalRevenue)}</div>
        <div className="kpi-sub">{formatCurrency(data.total_refunds_cents || 0)} refunded</div>
      </div>
      <div className="kpi-card">
        <div className="kpi-label">NPS</div>
        <div className="kpi-value" style={{ color: npsColor }}>{nps != null ? nps : "N/A"}</div>
        <div className="kpi-sub">-100 to +100 scale</div>
      </div>
    </div>
  );
}
