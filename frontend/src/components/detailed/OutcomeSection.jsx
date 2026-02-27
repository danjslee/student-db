import { useState, useEffect } from "react";
import {
  fetchConfidenceDistribution, fetchConfidenceAfterDistribution,
  fetchNpsDistribution,
  fetchTransformationalDistribution, fetchDeliveredOnPromiseDistribution,
} from "../../api";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Cell, Legend,
} from "recharts";
import { colors, npsColor, tooltipStyle, axisProps, gridProps } from "../../chartTheme";
import DonutChart from "./DonutChart";

export default function OutcomeSection({ productIds }) {
  const [confBefore, setConfBefore] = useState([]);
  const [confAfter, setConfAfter] = useState([]);
  const [npsData, setNpsData] = useState([]);
  const [transData, setTransData] = useState([]);
  const [deliveredData, setDeliveredData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchConfidenceDistribution(productIds),
      fetchConfidenceAfterDistribution(productIds),
      fetchNpsDistribution(productIds),
      fetchTransformationalDistribution(productIds),
      fetchDeliveredOnPromiseDistribution(productIds),
    ])
      .then(([before, after, nps, trans, delivered]) => {
        setConfBefore(before);
        setConfAfter(after);
        setNpsData(nps);
        setTransData(trans);
        setDeliveredData(delivered);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [productIds]);

  if (loading) {
    return (
      <div className="charts-grid">
        {[1,2,3,4].map(i => (
          <div key={i} className="chart-card skeleton-card">
            <div className="skeleton-bar" style={{ width: "40%", height: 16, marginBottom: 16 }} />
            <div className="skeleton-bar" style={{ width: "100%", height: 200 }} />
          </div>
        ))}
      </div>
    );
  }

  // Merge confidence before/after into combined data
  const allLevels = new Set();
  confBefore.forEach((d) => allLevels.add(d.label));
  confAfter.forEach((d) => allLevels.add(d.label));
  const beforeMap = Object.fromEntries(confBefore.map((d) => [d.label, d.count]));
  const afterMap = Object.fromEntries(confAfter.map((d) => [d.label, d.count]));
  const totalBefore = confBefore.reduce((s, d) => s + d.count, 0);
  const totalAfter = confAfter.reduce((s, d) => s + d.count, 0);
  const confidenceComparison = [...allLevels]
    .sort((a, b) => parseInt(a) - parseInt(b))
    .map((level) => ({
      label: level,
      before: totalBefore > 0 ? Math.round(((beforeMap[level] || 0) / totalBefore) * 100) : 0,
      after: totalAfter > 0 ? Math.round(((afterMap[level] || 0) / totalAfter) * 100) : 0,
    }));

  // Calculate NPS score
  const totalNps = npsData.reduce((s, d) => s + d.count, 0);
  const promoters = npsData.filter((d) => parseInt(d.label) >= 9).reduce((s, d) => s + d.count, 0);
  const detractors = npsData.filter((d) => parseInt(d.label) <= 6).reduce((s, d) => s + d.count, 0);
  const npsScore = totalNps > 0 ? Math.round(((promoters - detractors) / totalNps) * 100) : null;

  // Outcome achieved placeholder (no data yet)
  const outcomeData = [
    { label: "Yes", count: 0 },
    { label: "No", count: 0 },
  ];

  return (
    <div className="charts-grid">
      {/* Combined Confidence Before/After */}
      <div className="chart-card full-width">
        <h3>Confidence: Before vs After</h3>
        {confidenceComparison.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={confidenceComparison} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="label" {...axisProps.x} />
              <YAxis allowDecimals={false} {...axisProps.y} tickFormatter={(v) => `${v}%`} />
              <Tooltip {...tooltipStyle} formatter={(v) => `${v}%`} />
              <Legend
                wrapperStyle={{ fontSize: 12, color: "#a8a29e" }}
                iconType="circle"
                iconSize={8}
              />
              <Bar dataKey="before" fill={colors.muted} radius={[4, 4, 0, 0]} name="Before" />
              <Bar dataKey="after" fill={colors.secondary} radius={[4, 4, 0, 0]} name="After" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="chart-empty">No confidence data.</p>
        )}
      </div>

      {/* NPS KPI + Distribution */}
      <div className="chart-card">
        <h3>Recommend Score (NPS)</h3>
        {npsScore !== null && (
          <div style={{ textAlign: "center", marginBottom: 12 }}>
            <span style={{
              fontSize: 42, fontWeight: 700,
              color: npsScore >= 50 ? colors.secondary : npsScore >= 0 ? colors.warm : colors.rose,
            }}>
              {npsScore}
            </span>
            <span style={{ fontSize: 14, color: "#78716c", marginLeft: 6 }}>NPS</span>
          </div>
        )}
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={npsData} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="label" {...axisProps.x} />
            <YAxis allowDecimals={false} {...axisProps.y} />
            <Tooltip {...tooltipStyle} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {npsData.map((entry, i) => (
                <Cell key={i} fill={npsColor(parseInt(entry.label) || 0)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Transformational score */}
      <div className="chart-card">
        <h3>Transformational Score</h3>
        {transData.length > 0 ? (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={transData} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="label" {...axisProps.x} />
              <YAxis allowDecimals={false} {...axisProps.y} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="count" fill={colors.tertiary} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="chart-empty">No data yet.</p>
        )}
      </div>

      {/* Delivered on promise */}
      <div className="chart-card">
        <h3>Delivered on Promise</h3>
        {deliveredData.length > 0 ? (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={deliveredData} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="label" {...axisProps.x} />
              <YAxis allowDecimals={false} {...axisProps.y} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="count" fill={colors.primary} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="chart-empty">No data yet.</p>
        )}
      </div>

      {/* Outcome Achieved */}
      <div className="chart-card">
        <h3>Outcome Achieved</h3>
        <p className="chart-empty">No data yet — will populate from future courses.</p>
      </div>
    </div>
  );
}
