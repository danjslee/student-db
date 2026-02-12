import { useState, useEffect } from "react";
import { fetchReferralSources, fetchHereForDistribution, fetchGetFromDistribution } from "../../api";
import DonutChart from "./DonutChart";
import HorizontalBar from "./HorizontalBar";
import { colors } from "../../chartTheme";

export default function DecisionToJoin({ productIds }) {
  const [referralData, setReferralData] = useState([]);
  const [hereForData, setHereForData] = useState([]);
  const [getFromData, setGetFromData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchReferralSources(productIds),
      fetchHereForDistribution(productIds),
      fetchGetFromDistribution(productIds),
    ])
      .then(([referrals, hereFor, getFrom]) => {
        setReferralData(referrals);
        setHereForData(hereFor);
        setGetFromData(getFrom);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [productIds]);

  if (loading) {
    return (
      <div className="charts-grid">
        {[1,2,3].map(i => (
          <div key={i} className="chart-card skeleton-card">
            <div className="skeleton-bar" style={{ width: "40%", height: 16, marginBottom: 16 }} />
            <div className="skeleton-bar" style={{ width: "100%", height: 200 }} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="charts-grid">
      <div className="chart-card">
        <h3>How did you learn about the course?</h3>
        <DonutChart data={referralData} />
      </div>

      <div className="chart-card">
        <h3>What are you here for?</h3>
        <HorizontalBar data={hereForData} color={colors.primary} />
      </div>

      <div className="chart-card">
        <h3>What do you want to get from this?</h3>
        <HorizontalBar data={getFromData} color={colors.secondary} />
      </div>
    </div>
  );
}
