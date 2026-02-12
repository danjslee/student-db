import { useState, useEffect, useRef, useCallback } from "react";
import { fetchProducts } from "../api";
import MultiSelectFilter from "./MultiSelectFilter";
import CohortSnapshot from "./detailed/CohortSnapshot";
import DecisionToJoin from "./detailed/DecisionToJoin";
import SurveyResponse from "./detailed/SurveyResponse";
import OutcomeSection from "./detailed/OutcomeSection";
import InsightsSection from "./detailed/InsightsSection";
import TestimonialSection from "./detailed/TestimonialSection";
import { colors } from "../chartTheme";

function useLazySection(ref) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!ref.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); observer.disconnect(); } },
      { rootMargin: "200px" }
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [ref]);
  return visible;
}

function LazySection({ title, children }) {
  const ref = useRef(null);
  const visible = useLazySection(ref);
  return (
    <div ref={ref} className="detail-section">
      <h2 className="section-heading">{title}</h2>
      {visible ? children : <div className="skeleton-card" style={{ height: 200 }} />}
    </div>
  );
}

export default function DetailedDataTab() {
  const [products, setProducts] = useState([]);
  const [selectedProducts, setSelectedProducts] = useState([]);

  useEffect(() => {
    fetchProducts()
      .then((prods) => {
        setProducts(prods);
        // Default: nothing selected = show all
      })
      .catch(console.error);
  }, []);

  const handleToggle = useCallback((id) => {
    setSelectedProducts((prev) => {
      if (prev.includes(id)) {
        return prev.filter((x) => x !== id);
      }
      return [...prev, id];
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelectedProducts([]);
  }, []);

  // When nothing selected, pass empty string (no filter = all data)
  const productIds = selectedProducts.length > 0 ? selectedProducts.join(",") : "";
  const isAllSelected = selectedProducts.length === 0;
  const chipItems = products.map((p) => ({ id: p.id, label: p.product_name }));

  return (
    <div className="insights-container">
      <div className="overview-toolbar">
        <button
          className="filter-chip"
          onClick={selectAll}
          style={isAllSelected ? { backgroundColor: colors.primary, borderColor: colors.primary, color: "#fff" } : {}}
        >
          All
        </button>
        <MultiSelectFilter
          items={chipItems}
          selected={selectedProducts}
          onToggle={handleToggle}
          label=""
        />
      </div>

      <LazySection title="Cohort Snapshot">
        <CohortSnapshot productIds={productIds} />
      </LazySection>

      <LazySection title="Decision to Join">
        <DecisionToJoin productIds={productIds} />
      </LazySection>

      <LazySection title="Survey Response">
        <SurveyResponse productIds={productIds} />
      </LazySection>

      <LazySection title="Outcome">
        <OutcomeSection productIds={productIds} />
      </LazySection>

      <LazySection title="Insights">
        <InsightsSection productIds={productIds} />
      </LazySection>

      <LazySection title="Testimonials">
        <TestimonialSection productIds={productIds} />
      </LazySection>
    </div>
  );
}
