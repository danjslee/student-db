import { useState, useEffect } from "react";
import {
  fetchStudentsByCountry, fetchStudentsByCity,
  fetchTimezoneDistribution, fetchAgeDistribution, fetchGenderDistribution,
} from "../../api";
import DonutChart from "./DonutChart";
import HorizontalBar from "./HorizontalBar";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine,
} from "recharts";
import { colors, tooltipStyle, axisProps, gridProps } from "../../chartTheme";

export default function CohortSnapshot({ productIds }) {
  const [countryData, setCountryData] = useState([]);
  const [cityData, setCityData] = useState([]);
  const [tzData, setTzData] = useState([]);
  const [ageData, setAgeData] = useState(null);
  const [genderData, setGenderData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchStudentsByCountry(null, productIds),
      fetchStudentsByCity(null, productIds),
      fetchTimezoneDistribution(productIds),
      fetchAgeDistribution(productIds),
      fetchGenderDistribution(productIds),
    ])
      .then(([countries, cities, tz, age, gender]) => {
        setCountryData(countries);
        setCityData(cities);
        setTzData(tz);
        setAgeData(age);
        setGenderData(gender);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [productIds]);

  if (loading) {
    return (
      <div className="charts-grid">
        {[1,2,3,4,5].map(i => (
          <div key={i} className="chart-card skeleton-card">
            <div className="skeleton-bar" style={{ width: "40%", height: 16, marginBottom: 16 }} />
            <div className="skeleton-bar" style={{ width: "100%", height: 200 }} />
          </div>
        ))}
      </div>
    );
  }

  // Country: top 8 + "Other" for donut
  const countryDonut = (() => {
    if (!countryData.length) return [];
    const top8 = countryData.slice(0, 8);
    const rest = countryData.slice(8);
    const other = rest.reduce((sum, c) => sum + c.count, 0);
    return other > 0 ? [...top8, { label: "Other", count: other }] : top8;
  })();

  // Timezone: shorten labels for display
  const tzDisplay = tzData.slice(0, 12).map((d) => {
    // Extract the short name like "EST (-5)" from long strings
    let short = d.label;
    const match = d.label.match(/^([A-Z]{2,4})/);
    const offsetMatch = d.label.match(/\(([^)]+)\)/);
    if (match && offsetMatch) {
      short = `${match[1]} (${offsetMatch[1]})`;
    } else if (d.label.length > 20) {
      short = d.label.substring(0, 18) + "...";
    }
    return { ...d, label: short };
  });

  return (
    <div className="charts-grid">
      <div className="chart-card">
        <h3>Country Distribution</h3>
        <DonutChart data={countryDonut} />
      </div>

      <div className="chart-card">
        <h3>City (Top 20)</h3>
        {cityData.length > 0 ? (
          <HorizontalBar data={cityData.slice(0, 20)} color={colors.secondary} />
        ) : (
          <p className="chart-empty">No city data.</p>
        )}
      </div>

      <div className="chart-card">
        <h3>Timezone Distribution</h3>
        {tzDisplay.length > 0 ? (
          <HorizontalBar data={tzDisplay} color={colors.primary} />
        ) : (
          <p className="chart-empty">No timezone data.</p>
        )}
      </div>

      <div className="chart-card">
        <h3>Age Distribution {ageData?.average_age ? `(avg: ${ageData.average_age})` : ""}</h3>
        {ageData?.buckets?.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={ageData.buckets} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="label" {...axisProps.x} />
              <YAxis allowDecimals={false} {...axisProps.y} />
              <Tooltip
                {...tooltipStyle}
                formatter={(val) => {
                  const ageTotal = ageData.buckets.reduce((s, b) => s + b.count, 0);
                  const pct = ageTotal > 0 ? Math.round((val / ageTotal) * 100) : 0;
                  return [`${val} (${pct}%)`, "Students"];
                }}
              />
              <Bar dataKey="count" fill={colors.tertiary} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="chart-empty">No age data.</p>
        )}
      </div>

      <div className="chart-card">
        <h3>Gender</h3>
        <DonutChart data={genderData} />
      </div>
    </div>
  );
}
