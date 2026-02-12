import { useState, useEffect } from "react";
import { fetchSatisfactionDistribution } from "../../api";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { colors, tooltipStyle, axisProps, gridProps } from "../../chartTheme";

export default function PostCourseSection({ productIds }) {
  const [satData, setSatData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchSatisfactionDistribution(productIds)
      .then(setSatData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [productIds]);

  if (loading) {
    return (
      <div className="chart-card skeleton-card">
        <div className="skeleton-bar" style={{ width: "40%", height: 16, marginBottom: 16 }} />
        <div className="skeleton-bar" style={{ width: "100%", height: 200 }} />
      </div>
    );
  }

  return (
    <div className="charts-grid">
      <div className="chart-card">
        <h3>Overall Satisfaction</h3>
        {satData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={satData} margin={{ top: 5, right: 20, bottom: 60, left: 10 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="label" angle={-45} textAnchor="end" interval={0} {...axisProps.x} />
              <YAxis allowDecimals={false} {...axisProps.y} />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="count" fill={colors.warm} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="chart-empty">No satisfaction data.</p>
        )}
      </div>
    </div>
  );
}
