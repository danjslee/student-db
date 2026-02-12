import { useState, useEffect, useCallback } from "react";
import { fetchTestimonials } from "../../api";

export default function TestimonialSection({ productIds }) {
  const [testimonials, setTestimonials] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchTestimonials(productIds)
      .then(setTestimonials)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [productIds]);

  const downloadCSV = useCallback(() => {
    if (!testimonials.length) return;
    const header = "Student,Course,Testimonial\n";
    const rows = testimonials.map((t) =>
      `"${(t.student_name || "").replace(/"/g, '""')}","${(t.product_name || "").replace(/"/g, '""')}","${(t.testimonial || "").replace(/"/g, '""')}"`
    ).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "testimonials.csv";
    a.click();
    URL.revokeObjectURL(url);
  }, [testimonials]);

  if (loading) {
    return (
      <div className="chart-card skeleton-card">
        <div className="skeleton-bar" style={{ width: "100%", height: 200 }} />
      </div>
    );
  }

  if (!testimonials.length) {
    return <p className="chart-empty">No testimonials yet.</p>;
  }

  return (
    <div>
      <button className="testimonial-download-btn" onClick={downloadCSV}>
        Download CSV ({testimonials.length})
      </button>
      <div className="testimonial-grid">
        {testimonials.map((t, i) => (
          <div key={i} className="testimonial-card">
            <div className="testimonial-text">"{t.testimonial}"</div>
            <div className="testimonial-author">
              {t.student_name} &mdash; {t.product_name}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
