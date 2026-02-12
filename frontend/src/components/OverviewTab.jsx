import { useState, useEffect, useCallback } from "react";
import { fetchProducts, fetchOverview } from "../api";
import MultiSelectFilter from "./MultiSelectFilter";
import KpiCards from "./overview/KpiCards";
import NpsTrendChart from "./overview/NpsTrendChart";
import RevenueChart from "./overview/RevenueChart";
import EnrollmentsChart from "./overview/EnrollmentsChart";
import ScholarshipsChart from "./overview/ScholarshipsChart";

const YEARS = [
  { id: "all", label: "All" },
  { id: "2025", label: "2025" },
  { id: "2026", label: "2026" },
];

export default function OverviewTab() {
  const [selectedYears, setSelectedYears] = useState(["all"]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const activeYear = selectedYears.includes("all") ? undefined : selectedYears[0];

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const overview = await fetchOverview(activeYear);
      setData(overview);
    } catch (err) {
      console.error("Failed to load overview:", err);
    } finally {
      setLoading(false);
    }
  }, [activeYear]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleYearToggle = (id) => {
    if (id === "all") {
      setSelectedYears(["all"]);
    } else {
      setSelectedYears([id]);
    }
  };

  return (
    <div className="insights-container">
      <div className="overview-toolbar">
        <MultiSelectFilter
          items={YEARS}
          selected={selectedYears}
          onToggle={handleYearToggle}
          label="Year:"
        />
      </div>
      {loading ? (
        <div className="charts-grid">
          {[1,2,3,4,5].map(i => (
            <div key={i} className="chart-card skeleton-card">
              <div className="skeleton-bar" style={{ width: "40%", height: 16, marginBottom: 16 }} />
              <div className="skeleton-bar" style={{ width: "100%", height: 200 }} />
            </div>
          ))}
        </div>
      ) : data ? (
        <>
          <KpiCards data={data} />
          <div className="charts-grid">
            <RevenueChart courses={data.courses} />
            <EnrollmentsChart courses={data.courses} />
            <NpsTrendChart courses={data.courses} />
            <ScholarshipsChart courses={data.courses} />
          </div>
        </>
      ) : (
        <p className="chart-empty">No data available.</p>
      )}
    </div>
  );
}
