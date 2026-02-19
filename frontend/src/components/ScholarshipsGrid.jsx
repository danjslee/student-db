import { useState, useEffect, useCallback, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { darkTheme } from "../gridTheme";
import { fetchScholarshipApplications, fetchProducts } from "../api";

const STATUS_OPTIONS = ["", "pending", "accepted", "rejected", "withdrawn"];

function DecisionCellRenderer(params) {
  const v = params.value || "";
  const colors = {
    pending: "#f59e0b",
    accepted: "#22c55e",
    rejected: "#ef4444",
    withdrawn: "#6b7280",
  };
  return (
    <span style={{ color: colors[v] || "#d6d3d1", fontWeight: 600 }}>
      {v || "—"}
    </span>
  );
}

function ProcessingStatusRenderer(params) {
  const v = params.value || "new";
  const colors = {
    processed: "#22c55e",
    new: "#f59e0b",
    manual: "#3b82f6",
  };
  const labels = {
    processed: "Processed",
    new: "New",
    manual: "Manual",
  };
  return (
    <span style={{ color: colors[v] || "#d6d3d1", fontWeight: 600 }}>
      {labels[v] || v}
    </span>
  );
}

export default function ScholarshipsGrid() {
  const [rowData, setRowData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("");

  useEffect(() => {
    fetchProducts().then(setProducts).catch(console.error);
  }, []);

  const loadData = useCallback(() => {
    setLoading(true);
    fetchScholarshipApplications({
      status: selectedStatus || undefined,
      product_id: selectedProduct || undefined,
    })
      .then(setRowData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedProduct, selectedStatus]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const columnDefs = useMemo(
    () => [
      { field: "id", headerName: "#", width: 60, editable: false },
      { field: "first_name", headerName: "First", width: 110, editable: false },
      { field: "last_name", headerName: "Last", width: 110, editable: false },
      { field: "email", headerName: "Email", width: 220, editable: false },
      { field: "product_name", headerName: "Course", width: 200, editable: false },
      {
        field: "is_subscriber",
        headerName: "Sub?",
        width: 70,
        editable: false,
        valueFormatter: (p) => (p.value === true ? "Yes" : p.value === false ? "No" : ""),
      },
      { field: "amount_willing_to_pay", headerName: "Can Pay", width: 90, editable: false },
      {
        field: "status",
        headerName: "Decision",
        width: 100,
        editable: false,
        cellRenderer: DecisionCellRenderer,
      },
      {
        field: "processing_status",
        headerName: "Status",
        width: 100,
        editable: false,
        cellRenderer: ProcessingStatusRenderer,
      },
      {
        field: "ai_recommended_tier",
        headerName: "AI Tier",
        width: 85,
        editable: false,
        valueFormatter: (p) => (p.value ? `$${p.value}` : ""),
      },
      {
        field: "decision_tier",
        headerName: "Tier",
        width: 75,
        editable: false,
        valueFormatter: (p) => (p.value ? `$${p.value}` : ""),
      },
      { field: "discount_code", headerName: "Code", width: 140, editable: false },
      {
        field: "enrolled",
        headerName: "Enrolled?",
        width: 90,
        editable: false,
        valueFormatter: (p) => (p.value ? "Yes" : ""),
      },
      {
        field: "kit_delivered",
        headerName: "Kit?",
        width: 70,
        editable: false,
        valueFormatter: (p) => (p.value ? "Yes" : ""),
      },
      {
        field: "applied_at",
        headerName: "Applied",
        width: 110,
        editable: false,
        valueFormatter: (p) => {
          if (!p.value) return "";
          return new Date(p.value).toLocaleDateString();
        },
      },
      {
        field: "decided_at",
        headerName: "Decided",
        width: 110,
        editable: false,
        valueFormatter: (p) => {
          if (!p.value) return "";
          return new Date(p.value).toLocaleDateString();
        },
      },
      { field: "circumstances", headerName: "Circumstances", width: 250, editable: false },
      { field: "hopes", headerName: "Hopes", width: 250, editable: false },
      { field: "best_case_impact", headerName: "Best Case Impact", width: 250, editable: false },
      { field: "ai_recommendation", headerName: "AI Rec", width: 300, editable: false },
      { field: "decision_notes", headerName: "Notes", width: 200, editable: false },
    ],
    []
  );

  const defaultColDef = useMemo(
    () => ({ sortable: true, resizable: true, filter: true }),
    []
  );

  const getRowId = useCallback((params) => String(params.data.id), []);

  return (
    <div className="grid-container">
      <div className="insights-toolbar" style={{ gap: "12px" }}>
        <div>
          <label htmlFor="schol-status-filter">Decision:</label>
          <select
            id="schol-status-filter"
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s || "All"}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="schol-course-filter">Course:</label>
          <select
            id="schol-course-filter"
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
        <span style={{ fontSize: "0.85em", opacity: 0.6 }}>
          {loading ? "Loading..." : `${rowData.length} application${rowData.length !== 1 ? "s" : ""}`}
        </span>
      </div>
      <div className="grid-wrapper">
        <AgGridReact
          theme={darkTheme}
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          getRowId={getRowId}
        />
      </div>
    </div>
  );
}
