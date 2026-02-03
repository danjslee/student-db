import { useState, useEffect } from "react";
import { fetchProducts, fetchStudentsByCountry, fetchStudentsByCity } from "../api";
import CountryChart from "./CountryChart";
import CityChart from "./CityChart";

export default function InsightsTab() {
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [countryData, setCountryData] = useState([]);
  const [cityData, setCityData] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch((err) => console.error("Failed to load products:", err));
  }, []);

  useEffect(() => {
    setLoading(true);
    const productId = selectedProduct || undefined;
    Promise.all([
      fetchStudentsByCountry(productId),
      fetchStudentsByCity(productId),
    ])
      .then(([countries, cities]) => {
        setCountryData(countries);
        setCityData(cities);
      })
      .catch((err) => console.error("Failed to load chart data:", err))
      .finally(() => setLoading(false));
  }, [selectedProduct]);

  return (
    <div className="insights-container">
      <div className="insights-toolbar">
        <label htmlFor="product-filter">Filter by product:</label>
        <select
          id="product-filter"
          value={selectedProduct}
          onChange={(e) => setSelectedProduct(e.target.value)}
        >
          <option value="">All Products</option>
          {products.map((p) => (
            <option key={p.id} value={p.id}>
              {p.product_name}
            </option>
          ))}
        </select>
      </div>
      {loading ? (
        <p className="chart-loading">Loading charts...</p>
      ) : (
        <div className="charts-grid">
          <CountryChart data={countryData} />
          <CityChart data={cityData} />
        </div>
      )}
    </div>
  );
}
