import { useState, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine,
} from "recharts";
import { seriesPalette, tooltipStyle, axisProps, gridProps } from "../../chartTheme";
import { fetchPurchaseTimeline } from "../../api";

const RATING_COLORS = { green: "#34d399", yellow: "#fbbf24", red: "#f87171" };
const RATING_LABELS = { green: "On Track", yellow: "Needs Push", red: "Behind" };

export default function PurchaseTimelineChart() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null); // product_slug

  useEffect(() => {
    fetchPurchaseTimeline()
      .then((d) => {
        setData(d);
        // Auto-select first upcoming course, or first course
        const upcoming = d.find((p) => p.is_upcoming);
        setSelected(upcoming ? upcoming.product_slug : d[0]?.product_slug);
      })
      .catch((err) => console.error("Failed to load purchase timeline:", err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="chart-card full-width">
        <h3>Purchase Timeline & Forecast</h3>
        <div className="skeleton-bar" style={{ width: "100%", height: 300 }} />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="chart-card full-width">
        <h3>Purchase Timeline & Forecast</h3>
        <p className="chart-empty">
          No timeline data. Set <code>course_start_date</code> on products to enable.
        </p>
      </div>
    );
  }

  // Build unified x-axis from all actual + forecast series
  const allDays = new Set();
  for (const product of data) {
    for (const point of product.actual_series) allDays.add(point.days_before);
    for (const point of product.forecast_series) allDays.add(point.days_before);
  }
  const sortedDays = [...allDays].sort((a, b) => b - a);

  // Build chart data rows
  const chartData = sortedDays.map((d) => {
    const row = { days_before: d };
    for (const product of data) {
      const slug = product.product_slug;
      // Actual: find closest point at or after this day (step-forward fill)
      let actual = null;
      for (const point of product.actual_series) {
        if (point.days_before >= d) actual = point.cumulative;
      }
      row[slug] = actual;

      // Forecast: only for upcoming, dotted line
      let forecast = null;
      for (const point of product.forecast_series) {
        if (point.days_before >= d) forecast = point.cumulative;
      }
      // Connect forecast to last actual point
      if (forecast !== null) {
        row[slug + "_forecast"] = forecast;
      }
    }
    return row;
  });

  // Ensure forecast line connects to the last actual data point
  for (const product of data) {
    if (product.actual_series.length > 0 && product.forecast_series.length > 0) {
      const lastActual = product.actual_series[product.actual_series.length - 1];
      const bridgeDay = lastActual.days_before;
      const bridgeRow = chartData.find((r) => r.days_before === bridgeDay);
      if (bridgeRow) {
        bridgeRow[product.product_slug + "_forecast"] = lastActual.cumulative;
      }
    }
  }

  const isAll = selected === "__all__";
  const selectedProduct = isAll ? null : data.find((p) => p.product_slug === selected);
  const fmtMoney = (cents) => "$" + Math.round(cents / 100).toLocaleString();

  return (
    <div className="chart-card full-width">
      <h3>Purchase Timeline & Forecast</h3>
      <p style={{ fontSize: 12, color: "#78716c", marginBottom: 12 }}>
        Cumulative sales by days before course start — dotted lines show forecast
      </p>

      {/* Course selector pills */}
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <button
          onClick={() => setSelected("__all__")}
          style={{
            padding: "6px 14px",
            borderRadius: 6,
            border: `1px solid ${selected === "__all__" ? "#fff" : "#292524"}`,
            background: selected === "__all__" ? "#ffffff15" : "transparent",
            color: selected === "__all__" ? "#fff" : "#78716c",
            fontSize: 13,
            fontWeight: selected === "__all__" ? 600 : 400,
            cursor: "pointer",
            transition: "all 0.15s",
          }}
        >
          All
        </button>
        {data.map((p, i) => {
          const isSelected = p.product_slug === selected;
          const color = seriesPalette[i % seriesPalette.length];
          return (
            <button
              key={p.product_slug}
              onClick={() => setSelected(p.product_slug)}
              style={{
                padding: "6px 14px",
                borderRadius: 6,
                border: `1px solid ${isSelected ? color : "#292524"}`,
                background: isSelected ? color + "20" : "transparent",
                color: isSelected ? color : "#78716c",
                fontSize: 13,
                fontWeight: isSelected ? 600 : 400,
                cursor: "pointer",
                transition: "all 0.15s",
              }}
            >
              {p.product_name}
              <span style={{ marginLeft: 6, fontSize: 11, opacity: 0.7 }}>
                {p.total_sales} sales
              </span>
            </button>
          );
        })}
      </div>

      <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
        {/* Chart */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid {...gridProps} />
              <XAxis
                dataKey="days_before"
                {...axisProps.x}
                reversed={false}
                tickFormatter={(v) => `${v}d`}
                label={{ value: "Days before course start", position: "insideBottom", offset: -10, fill: "#78716c", fontSize: 11 }}
              />
              <YAxis
                {...axisProps.y}
                allowDecimals={false}
                label={{ value: "Sales", angle: -90, position: "insideLeft", fill: "#78716c", fontSize: 11 }}
              />
              <Tooltip
                {...tooltipStyle}
                labelFormatter={(v) => `${v} days before start`}
                formatter={(val, name) => {
                  if (val == null) return [null, null];
                  const isForecast = name.includes("(forecast)");
                  return [Math.round(val) + " sales" + (isForecast ? " (projected)" : ""), name.replace(" (forecast)", "")];
                }}
              />
              {/* Target reference line for selected product (hidden in All view) */}
              {!isAll && selectedProduct?.sales_target && (
                <ReferenceLine
                  y={selectedProduct.sales_target}
                  stroke="#34d399"
                  strokeDasharray="6 3"
                  label={{ value: `Target: ${selectedProduct.sales_target}`, position: "right", fill: "#34d399", fontSize: 11 }}
                />
              )}
              {/* Actual lines */}
              {data.map((product, i) => (
                <Line
                  key={product.product_slug}
                  dataKey={product.product_slug}
                  stroke={seriesPalette[i % seriesPalette.length]}
                  strokeWidth={isAll || product.product_slug === selected ? 2.5 : 1.5}
                  strokeOpacity={isAll ? 1 : (product.product_slug === selected ? 1 : 0.3)}
                  dot={false}
                  name={product.product_name}
                  connectNulls
                />
              ))}
              {/* Forecast (dotted) lines */}
              {data.filter((p) => p.forecast_series.length > 0).map((product, i) => {
                const idx = data.indexOf(product);
                return (
                  <Line
                    key={product.product_slug + "_forecast"}
                    dataKey={product.product_slug + "_forecast"}
                    stroke={seriesPalette[idx % seriesPalette.length]}
                    strokeWidth={isAll || product.product_slug === selected ? 2.5 : 1.5}
                    strokeOpacity={isAll ? 0.7 : (product.product_slug === selected ? 0.7 : 0.2)}
                    strokeDasharray="8 4"
                    dot={false}
                    name={product.product_name + " (forecast)"}
                    connectNulls
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Summary panel for selected course */}
        {selectedProduct && (
          <div style={{
            width: 220,
            flexShrink: 0,
            background: "#12141c",
            border: "1px solid #292524",
            borderRadius: 10,
            padding: 16,
          }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#fff", marginBottom: 12 }}>
              {selectedProduct.product_name}
            </div>

            {/* Rating badge */}
            {selectedProduct.rating && (
              <div style={{
                display: "inline-block",
                padding: "4px 10px",
                borderRadius: 4,
                fontSize: 12,
                fontWeight: 600,
                color: "#0a0b0f",
                background: RATING_COLORS[selectedProduct.rating],
                marginBottom: 12,
              }}>
                {RATING_LABELS[selectedProduct.rating]}
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <StatRow label="Actual Sales" value={selectedProduct.total_sales} />
              <StatRow label="Actual Revenue" value={fmtMoney(selectedProduct.total_revenue_cents)} />

              {selectedProduct.is_upcoming && (
                <>
                  <div style={{ borderTop: "1px solid #292524", margin: "2px 0" }} />
                  <StatRow
                    label="Forecast Sales"
                    value={selectedProduct.forecast_total_sales ?? "—"}
                    highlight
                  />
                  <StatRow
                    label="Forecast Revenue"
                    value={selectedProduct.forecast_total_revenue_cents ? fmtMoney(selectedProduct.forecast_total_revenue_cents) : "—"}
                    highlight
                  />
                  {selectedProduct.sales_target && (
                    <StatRow
                      label="Target"
                      value={selectedProduct.sales_target}
                    />
                  )}
                  <StatRow
                    label="Avg Price"
                    value={fmtMoney(selectedProduct.avg_price_cents)}
                  />
                  <StatRow
                    label="Days to Go"
                    value={selectedProduct.days_until_start}
                  />
                </>
              )}

              {!selectedProduct.is_upcoming && (
                <>
                  <div style={{ borderTop: "1px solid #292524", margin: "2px 0" }} />
                  <StatRow label="Avg Price" value={fmtMoney(selectedProduct.avg_price_cents)} />
                  <StatRow label="Median Lead" value={`${selectedProduct.median_days_before}d`} />
                  <div style={{ fontSize: 11, color: "#555", marginTop: 4 }}>
                    Completed — used as benchmark
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatRow({ label, value, highlight }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "#78716c", textTransform: "uppercase", letterSpacing: "0.04em" }}>
        {label}
      </div>
      <div style={{ fontSize: 18, fontWeight: 700, color: highlight ? "#60a5fa" : "#fff" }}>
        {value}
      </div>
    </div>
  );
}
