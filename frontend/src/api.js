const BASE_URL = "http://localhost:8000/api";

// ── Students ──────────────────────────────────────────────

export async function fetchStudents({ skip = 0, limit = 200, search, country, city } = {}) {
  const params = new URLSearchParams();
  params.set("skip", skip);
  params.set("limit", limit);
  if (search) params.set("search", search);
  if (country) params.set("country", country);
  if (city) params.set("city", city);
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

// ── Analytics ────────────────────────────────────────────

export async function fetchStudentsByCountry(productId) {
  const params = new URLSearchParams();
  if (productId) params.set("product_id", productId);
  const res = await fetch(`${BASE_URL}/analytics/students-by-country?${params}`);
  if (!res.ok) throw new Error(`Failed to fetch students by country: ${res.status}`);
  return res.json();
}

export async function fetchStudentsByCity(productId) {
  const params = new URLSearchParams();
  if (productId) params.set("product_id", productId);
  const res = await fetch(`${BASE_URL}/analytics/students-by-city?${params}`);
  if (!res.ok) throw new Error(`Failed to fetch students by city: ${res.status}`);
  return res.json();
}

// ── Chat ─────────────────────────────────────────────────

export async function sendChatMessage(message) {
  const res = await fetch(`${BASE_URL}/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(`Chat request failed: ${res.status}`);
  return res.json();
}
