// Design system for all charts — single source of truth for colors, tooltips, axes
export const colors = {
  primary: "#6d9eeb",
  secondary: "#81c784",
  tertiary: "#ce93d8",
  warm: "#f4a261",
  rose: "#e57373",
  muted: "#90a4ae",
};

// Ordered series palette for multi-series charts
export const seriesPalette = [
  colors.primary,
  colors.secondary,
  colors.tertiary,
  colors.warm,
  colors.rose,
  colors.muted,
];

// NPS zone colors: 0-6 detractor, 7-8 passive, 9-10 promoter
export const npsColor = (score) => {
  if (score >= 9) return colors.secondary;
  if (score >= 7) return colors.warm;
  return colors.rose;
};

// Enrollment status color map
export const statusColors = {
  "Full Fee": colors.primary,
  "Early Bird": "#4fc3f7",
  "Scholarship": colors.tertiary,
  "Free Place": colors.muted,
  "Refunded": colors.rose,
  "Deferred": colors.warm,
};

// Standard legend props — positioned at top to avoid x-axis label overlap
export const legendProps = {
  verticalAlign: "top",
  align: "right",
  wrapperStyle: { fontSize: 12, color: "#a8a29e", paddingBottom: 8 },
  iconType: "circle",
  iconSize: 8,
};

// Multi-line tick for horizontal x-axis labels (wraps long course names)
export function MultiLineTick({ x, y, payload }) {
  const text = payload.value || "";
  const words = text.split(/\s+/);
  const lines = [];
  let current = "";
  for (const word of words) {
    if (current && (current + " " + word).length > 18) {
      lines.push(current);
      current = word;
    } else {
      current = current ? current + " " + word : word;
    }
  }
  if (current) lines.push(current);

  return (
    <g transform={`translate(${x},${y})`}>
      {lines.map((line, i) => (
        <text key={i} x={0} y={0} dy={i * 14 + 14} textAnchor="middle" fill="#78716c" fontSize={11}>
          {line}
        </text>
      ))}
    </g>
  );
}

// Shared tooltip style
export const tooltipStyle = {
  contentStyle: {
    backgroundColor: "#1c1917",
    border: "1px solid #292524",
    borderRadius: "8px",
    color: "#fff",
    fontSize: "13px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
  },
  labelStyle: { color: "#a8a29e", fontWeight: 600, marginBottom: 4 },
  itemStyle: { color: "#fff" },
  cursor: { fill: "rgba(255,255,255,0.04)" },
};

// Shared axis config
export const axisProps = {
  x: {
    tick: { fontSize: 11, fill: "#78716c" },
    axisLine: { stroke: "#292524" },
    tickLine: false,
  },
  y: {
    tick: { fontSize: 11, fill: "#78716c" },
    axisLine: false,
    tickLine: false,
  },
};

export const gridProps = {
  strokeDasharray: "3 3",
  stroke: "#1c1917",
  vertical: false,
};

// Formatter for cents → dollar string
export const formatCurrency = (cents) => {
  if (cents == null) return "$0";
  return `$${(cents / 100).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
};
