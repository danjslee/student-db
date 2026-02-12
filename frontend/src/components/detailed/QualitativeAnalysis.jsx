import { useState, useCallback } from "react";
import { fetchQualitativeAnalysis } from "../../api";

export default function QualitativeAnalysis({ productIds, field }) {
  const [themes, setThemes] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchQualitativeAnalysis(productIds, field);
      setThemes(result.themes || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [productIds, field]);

  if (!themes && !loading) {
    return (
      <div>
        <button className="qual-generate-btn" onClick={generate} disabled={loading}>
          Generate Analysis
        </button>
        {error && <p style={{ color: "#e57373", fontSize: 13, marginTop: 8 }}>{error}</p>}
      </div>
    );
  }

  if (loading) {
    return <p className="chart-loading">Analyzing responses...</p>;
  }

  if (!themes || themes.length === 0) {
    return <p className="chart-empty">No themes found.</p>;
  }

  return (
    <div>
      {themes.map((theme, i) => (
        <div key={i} className="theme-card">
          <div className="theme-title">
            <span>{i + 1}.</span>
            <span>{theme.title}</span>
            <span style={{ marginLeft: "auto", fontSize: 12, color: "#78716c" }}>
              {theme.count} mention{theme.count !== 1 ? "s" : ""}
            </span>
          </div>
          <div className="theme-weight-bar">
            <div className="theme-weight-fill" style={{ width: `${theme.weight * 100}%` }} />
          </div>
          {theme.quotes && theme.quotes.length > 0 && (
            <details>
              <summary style={{ cursor: "pointer", color: "#78716c", fontSize: 13 }}>
                Example quotes
              </summary>
              <div className="theme-quotes">
                {theme.quotes.map((q, j) => (
                  <div key={j} className="theme-quote">"{q}"</div>
                ))}
              </div>
            </details>
          )}
        </div>
      ))}
      <button
        className="qual-generate-btn"
        onClick={generate}
        style={{ marginTop: 12 }}
      >
        Regenerate
      </button>
    </div>
  );
}
