const BASE_URL = window.location.hostname === "localhost"
  ? "http://localhost:8000/api"
  : "/api";

// ── Students ──────────────────────────────────────────────

export async function fetchStudents({ skip = 0, limit = 200, search, country, city, product_id } = {}) {
  const params = new URLSearchParams();
  params.set("skip", skip);
  params.set("limit", limit);
  if (search) params.set("search", search);
  if (country) params.set("country", country);
  if (city) params.set("city", city);
  if (product_id) params.set("product_id", product_id);
  const res = await fetch(`${BASE_URL}/students/?${params}`);
  if (!res.ok) throw new Error(`Failed to fetch students: ${res.status}`);
  return res.json();
}

export async function updateStudent(id, fields) {
  const res = await fetch(`${BASE_URL}/students/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
  if (!res.ok) throw new Error(`Failed to update student: ${res.status}`);
  return res.json();
}

export async function deleteStudent(id) {
  const res = await fetch(`${BASE_URL}/students/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete student: ${res.status}`);
  return res.json();
}

// ── Products ──────────────────────────────────────────────

export async function fetchProducts() {
  const res = await fetch(`${BASE_URL}/products/`);
  if (!res.ok) throw new Error(`Failed to fetch products: ${res.status}`);
  return res.json();
}

export async function updateProduct(id, fields) {
  const res = await fetch(`${BASE_URL}/products/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
  if (!res.ok) throw new Error(`Failed to update product: ${res.status}`);
  return res.json();
}

export async function deleteProduct(id) {
  const res = await fetch(`${BASE_URL}/products/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete product: ${res.status}`);
  return res.json();
}

// ── Enrollments ───────────────────────────────────────────

export async function fetchEnrollments({ skip = 0, limit = 200, status, product_id, student_id } = {}) {
  const params = new URLSearchParams();
  params.set("skip", skip);
  params.set("limit", limit);
  if (status) params.set("status", status);
  if (product_id) params.set("product_id", product_id);
  if (student_id) params.set("student_id", student_id);
  const res = await fetch(`${BASE_URL}/enrollments/?${params}`);
  if (!res.ok) throw new Error(`Failed to fetch enrollments: ${res.status}`);
  return res.json();
}

export async function updateEnrollment(id, fields) {
  const res = await fetch(`${BASE_URL}/enrollments/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
  if (!res.ok) throw new Error(`Failed to update enrollment: ${res.status}`);
  return res.json();
}

export async function deleteEnrollment(id) {
  const res = await fetch(`${BASE_URL}/enrollments/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete enrollment: ${res.status}`);
  return res.json();
}

// ── Analytics — Overview ─────────────────────────────────

export async function fetchOverview(year) {
  const params = new URLSearchParams();
  if (year) params.set("year", year);
  const res = await fetch(`${BASE_URL}/analytics/overview?${params}`);
  if (!res.ok) throw new Error(`Failed to fetch overview: ${res.status}`);
  return res.json();
}

export async function fetchPurchaseTimeline() {
  const res = await fetch(`${BASE_URL}/analytics/purchase-timeline`);
  if (!res.ok) throw new Error(`Failed to fetch purchase timeline: ${res.status}`);
  return res.json();
}

// ── Analytics — Distributions (support product_ids) ──────

function _analyticsUrl(path, productIds) {
  const params = new URLSearchParams();
  if (productIds) params.set("product_ids", productIds);
  return `${BASE_URL}/analytics/${path}?${params}`;
}

export async function fetchStudentsByCountry(productId, productIds) {
  const params = new URLSearchParams();
  if (productId) params.set("product_id", productId);
  if (productIds) params.set("product_ids", productIds);
  const res = await fetch(`${BASE_URL}/analytics/students-by-country?${params}`);
  if (!res.ok) throw new Error(`Failed to fetch students by country: ${res.status}`);
  return res.json();
}

export async function fetchStudentsByCity(productId, productIds) {
  const params = new URLSearchParams();
  if (productId) params.set("product_id", productId);
  if (productIds) params.set("product_ids", productIds);
  const res = await fetch(`${BASE_URL}/analytics/students-by-city?${params}`);
  if (!res.ok) throw new Error(`Failed to fetch students by city: ${res.status}`);
  return res.json();
}

export async function fetchTimezoneDistribution(productIds) {
  const res = await fetch(_analyticsUrl("timezone-distribution", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export async function fetchAgeDistribution(productIds) {
  const res = await fetch(_analyticsUrl("age-distribution", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export async function fetchGenderDistribution(productIds) {
  const res = await fetch(_analyticsUrl("gender-distribution", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export async function fetchReferralSources(productIds) {
  const res = await fetch(_analyticsUrl("referral-sources", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export async function fetchHereForDistribution(productIds) {
  const res = await fetch(_analyticsUrl("here-for-distribution", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export async function fetchGetFromDistribution(productIds) {
  const res = await fetch(_analyticsUrl("get-from-distribution", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export async function fetchSurveyResponseRates(productIds) {
  const res = await fetch(_analyticsUrl("survey-response-rates", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export async function fetchConfidenceDistribution(productIds) {
  const res = await fetch(_analyticsUrl("confidence-distribution", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export async function fetchConfidenceAfterDistribution(productIds) {
  const res = await fetch(_analyticsUrl("confidence-after-distribution", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export async function fetchSatisfactionDistribution(productIds) {
  const res = await fetch(_analyticsUrl("satisfaction-distribution", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export async function fetchNpsDistribution(productIds) {
  const res = await fetch(_analyticsUrl("nps-distribution", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export async function fetchTransformationalDistribution(productIds) {
  const res = await fetch(_analyticsUrl("transformational-distribution", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

export async function fetchDeliveredOnPromiseDistribution(productIds) {
  const res = await fetch(_analyticsUrl("delivered-on-promise-distribution", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

// ── Analytics — Qualitative ──────────────────────────────

export async function fetchQualitativeAnalysis(productIds, field) {
  const res = await fetch(`${BASE_URL}/analytics/qualitative`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_ids: productIds, field }),
  });
  if (!res.ok) throw new Error(`Qualitative analysis failed: ${res.status}`);
  return res.json();
}

// ── Analytics — Testimonials ─────────────────────────────

export async function fetchTestimonials(productIds) {
  const res = await fetch(_analyticsUrl("testimonials", productIds));
  if (!res.ok) throw new Error(`Failed: ${res.status}`);
  return res.json();
}

// ── Sales ─────────────────────────────────────────────────

export async function fetchSales({ skip = 0, limit = 200, product_id, status } = {}) {
  const params = new URLSearchParams();
  params.set("skip", skip);
  params.set("limit", limit);
  if (product_id) params.set("product_id", product_id);
  if (status) params.set("status", status);
  const res = await fetch(`${BASE_URL}/sales/?${params}`);
  if (!res.ok) throw new Error(`Failed to fetch sales: ${res.status}`);
  return res.json();
}

export async function updateSale(id, fields) {
  const res = await fetch(`${BASE_URL}/sales/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
  if (!res.ok) throw new Error(`Failed to update sale: ${res.status}`);
  return res.json();
}

export async function importSalesCSV(productId, file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE_URL}/sales/import-csv?product_id=${encodeURIComponent(productId)}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`CSV import failed: ${detail}`);
  }
  return res.json();
}

// ── Chat ─────────────────────────────────────────────────

export async function sendChatMessage(messages) {
  const res = await fetch(`${BASE_URL}/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
  if (!res.ok) throw new Error(`Chat request failed: ${res.status}`);
  return res.json();
}
