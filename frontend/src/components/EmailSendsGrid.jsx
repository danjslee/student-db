import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { AgGridReact } from "ag-grid-react";
import { darkTheme } from "../gridTheme";
import { fetchEmailSends, fetchProducts } from "../api";

const EMAIL_TYPE_LABELS = {
  onboarding_confirmation: "Onboarding Confirmation",
  enrollment_confirmation: "Enrollment Confirmation",
  form_reminder: "Form Reminder",
  welcome: "Welcome",
  project_circle: "Project + Circle",
  tomorrow: "Tomorrow Checklist",
  thanks_survey: "Thanks + Survey",
  survey_nudge: "Survey Nudge",
  recording_discount: "Recording + Discount",
  deferred_invite: "Deferred Invite",
};

function formatEmailType(type) {
  if (!type) return "\u2014";
  return EMAIL_TYPE_LABELS[type] || type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function SendStatusRenderer(params) {
  const v = params.value || "";
  const colors = {
    dry_run: "#f59e0b",
    sent: "#3b82f6",
    delivered: "#22c55e",
    error: "#ef4444",
    bounced: "#ef4444",
    complained: "#ef4444",
    pending: "#6b7280",
  };
  return (
    <span style={{ color: colors[v] || "#d6d3d1", fontWeight: 600 }}>
      {v || "\u2014"}
    </span>
  );
}

function formatDateTime(iso) {
  if (!iso) return "\u2014";
  const d = new Date(iso + "Z");
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

export default function EmailSendsGrid() {
  const [rowData, setRowData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [selectedType, setSelectedType] = useState("");
  const [searchText, setSearchText] = useState("");
  const debounceRef = useRef(null);

  useEffect(() => {
    fetchProducts().then(setProducts).catch(console.error);
  }, []);

  const loadData = useCallback((filters = {}) => {
    setLoading(true);
    fetchEmailSends(filters)
      .then(setRowData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // Build filters and fetch
  const currentFilters = useCallback(() => {
    const f = {};
    if (searchText.trim()) f.to_email = searchText.trim();
    if (selectedProduct) f.product_id = selectedProduct;
    if (selectedType) f.email_type = selectedType;
    return f;
  }, [searchText, selectedProduct, selectedType]);

  // Initial load
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Re-fetch on dropdown filter change
  useEffect(() => {
    loadData(currentFilters());
  }, [selectedProduct, selectedType]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounced search
  const handleSearchChange = useCallback((e) => {
    const val = e.target.value;
    setSearchText(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      loadData({ ...currentFilters(), to_email: val.trim() || undefined });
    }, 400);
  }, [loadData, currentFilters]);

  const columnDefs = useMemo(
    () => [
      { field: "to_email", headerName: "Recipient", width: 250, editable: false },
      {
        field: "email_type",
        headerName: "Email Type",
        width: 170,
        editable: false,
        valueFormatter: (p) => formatEmailType(p.value),
      },
      {
        field: "status",
        headerName: "Status",
        width: 100,
        editable: false,
        cellRenderer: SendStatusRenderer,
      },
      { field: "subject", headerName: "Subject", width: 300, editable: false },
      {
        field: "sent_at",
        headerName: "Sent At",
        width: 160,
        editable: false,
        valueFormatter: (p) => formatDateTime(p.value),
      },
      {
        field: "error_message",
        headerName: "Error",
        width: 200,
        editable: false,
        cellStyle: (p) => p.value ? { color: "#ef4444" } : null,
      },
    ],
    []
  );

  const defaultColDef = useMemo(
    () => ({ sortable: true, resizable: true, filter: true }),
    []
  );

  return (
    <div className="grid-container">
      <div className="insights-toolbar" style={{ gap: "12px" }}>
        <div>
          <label htmlFor="es-search">Student:</label>
          <input
            id="es-search"
            type="text"
            placeholder="Search by email..."
            value={searchText}
            onChange={handleSearchChange}
            style={{
              padding: "4px 8px",
              background: "#1c1917",
              border: "1px solid #292524",
              color: "#d6d3d1",
              borderRadius: "3px",
              width: "220px",
            }}
          />
        </div>
        <div>
          <label htmlFor="es-course-filter">Course:</label>
          <select
            id="es-course-filter"
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
          >
            <option value="">All</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.product_name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="es-type-filter">Type:</label>
          <select
            id="es-type-filter"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
          >
            <option value="">All</option>
            {Object.entries(EMAIL_TYPE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <span style={{ fontSize: "0.85em", opacity: 0.6 }}>
          {loading ? "Loading..." : `${rowData.length} send${rowData.length !== 1 ? "s" : ""}`}
        </span>
      </div>

      <div className="grid-wrapper">
        <AgGridReact
          theme={darkTheme}
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          getRowId={useCallback((params) => String(params.data.id), [])}
        />
      </div>
    </div>
  );
}
