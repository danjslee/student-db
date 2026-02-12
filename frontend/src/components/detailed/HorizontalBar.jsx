import { colors } from "../../chartTheme";

export default function HorizontalBar({ data, color = colors.primary }) {
  if (!data || data.length === 0) {
    return <p className="chart-empty">No data available.</p>;
  }

  const maxCount = Math.max(...data.map((d) => d.count));
  const total = data.reduce((sum, d) => sum + d.count, 0);

  return (
    <div>
      {data.map((item, i) => {
        const pct = total > 0 ? Math.round((item.count / total) * 100) : 0;
        return (
          <div key={i} className="hbar-row" title={`${item.label}: ${item.count} (${pct}%)`}>
            <span className="hbar-label" title={item.label}>{item.label}</span>
            <div className="hbar-track">
              <div
                className="hbar-fill"
                style={{
                  width: `${maxCount > 0 ? (item.count / maxCount) * 100 : 0}%`,
                  backgroundColor: color,
                }}
              />
            </div>
            <span className="hbar-count">{pct}% <span style={{ color: "#78716c", fontSize: 11 }}>({item.count})</span></span>
          </div>
        );
      })}
    </div>
  );
}
