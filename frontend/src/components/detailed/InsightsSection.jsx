import QualitativeAnalysis from "./QualitativeAnalysis";

export default function InsightsSection({ productIds }) {
  return (
    <div className="charts-grid">
      <div className="chart-card">
        <h3>#1 Feature That Made You Join</h3>
        <QualitativeAnalysis productIds={productIds} field="what_made_you_join" />
      </div>

      <div className="chart-card">
        <h3>Three Things Learned</h3>
        <QualitativeAnalysis productIds={productIds} field="three_things_learned" />
      </div>

      <div className="chart-card">
        <h3>Ways to Improve</h3>
        <QualitativeAnalysis productIds={productIds} field="improvement_suggestion" />
      </div>

      <div className="chart-card">
        <h3>Biggest Wins</h3>
        <QualitativeAnalysis productIds={productIds} field="biggest_win" />
      </div>
    </div>
  );
}
