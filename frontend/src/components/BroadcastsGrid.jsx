import { useState, useEffect, useCallback, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { darkTheme } from "../gridTheme";
import {
  fetchBroadcasts,
  fetchBroadcastSends,
  fetchTriggeredEmails,
  fetchProducts,
  cancelBroadcast,
} from "../api";

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

// Trigger-based email types — always show these even with 0 sends
const TRIGGER_EMAIL_TYPES = [
  { email_type: "onboarding_confirmation", name: "Onboarding Confirmation", description: "On enrollment" },
  { email_type: "form_reminder", name: "Form Reminder", description: "3 days post-enrollment if form not done" },
  { email_type: "recording_discount", name: "Recording + Discount", description: "On survey completion" },
  { email_type: "deferred_invite", name: "Deferred Invite", description: "Manual trigger" },
];

function formatEmailType(type) {
  if (!type) return "\u2014";
  return EMAIL_TYPE_LABELS[type] || type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function StatusRenderer(params) {
  const row = params.data;
  const v = row.status || "";
  const isDryRun = row.dry_run;

  if (row._type === "broadcast") {
    if (v === "sent" && isDryRun) {
      return <span style={{ color: "#f59e0b", fontWeight: 600 }}>Dry Run Complete</span>;
    }
    if (v === "sent" && !isDryRun) {
      return <span style={{ color: "#22c55e", fontWeight: 600 }}>Sent</span>;
    }
    if (v === "pending" && isDryRun) {
      return <span style={{ color: "#6b7280", fontWeight: 600 }}>Pending (Dry Run)</span>;
    }
  }

  const colors = {
    pending: "#f59e0b",
    sending: "#3b82f6",
    sent: "#22c55e",
    delivered: "#22c55e",
    dry_run: "#f59e0b",
    active: "#a78bfa",
    partial_error: "#ef4444",
    error: "#ef4444",
    cancelled: "#6b7280",
  };
  const labels = {
    pending: "Pending",
    sending: "Sending\u2026",
    sent: "Sent",
    delivered: "Delivered",
    dry_run: "Dry Run",
    active: "Active",
    partial_error: "Errors",
    error: "Error",
    cancelled: "Cancelled",
  };
  return (
    <span style={{ color: colors[v] || "#d6d3d1", fontWeight: 600 }}>
      {labels[v] || v || "\u2014"}
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

export default function BroadcastsGrid() {
  const [rowData, setRowData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [selectedRow, setSelectedRow] = useState(null);
  const [sendData, setSendData] = useState([]);
  const [sendsLoading, setSendsLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    fetchProducts().then(setProducts).catch(console.error);
  }, []);

  const loadData = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetchBroadcasts(),
      fetchTriggeredEmails(),
    ])
      .then(([broadcasts, triggered]) => {
        const broadcastRows = broadcasts.map((b) => ({
          ...b,
          _type: "broadcast",
          _id: "b-" + b.id,
          _schedule: b.scheduled_at ? formatDateTime(b.scheduled_at) : "\u2014",
          _email_type_label: formatEmailType(b.email_type),
        }));

        // Build trigger rows — start with empty shells for all known types
        const triggerGroups = {};
        for (const t of TRIGGER_EMAIL_TYPES) {
          triggerGroups[t.email_type] = {
            _type: "triggered",
            _id: "t-" + t.email_type,
            id: null,
            name: t.name,
            email_type: t.email_type,
            _email_type_label: t.name,
            _description: t.description,
            status: "active",
            dry_run: false,
            scheduled_at: null,
            _schedule: "On trigger",
            product_id: null,
            total_recipients: 0,
            sent_count: 0,
            error_count: 0,
            sends: [],
          };
        }

        // Merge actual send data into trigger rows
        for (const send of triggered) {
          const key = send.email_type || "unknown";
          if (!triggerGroups[key]) {
            triggerGroups[key] = {
              _type: "triggered",
              _id: "t-" + key,
              id: null,
              name: formatEmailType(key),
              email_type: key,
              _email_type_label: formatEmailType(key),
              _description: "",
              status: "active",
              dry_run: false,
              scheduled_at: null,
              _schedule: "On trigger",
              product_id: send.product_id,
              total_recipients: 0,
              sent_count: 0,
              error_count: 0,
              sends: [],
            };
          }
          if (send.product_id) triggerGroups[key].product_id = send.product_id;
          triggerGroups[key].total_recipients += 1;
          if (send.status === "sent" || send.status === "delivered") {
            triggerGroups[key].sent_count += 1;
          } else if (send.status === "dry_run") {
            triggerGroups[key].sent_count += 1;
          } else if (send.status === "error") {
            triggerGroups[key].error_count += 1;
          }
          triggerGroups[key].sends.push(send);
        }

        const triggerRows = Object.values(triggerGroups);
        setRowData([...broadcastRows, ...triggerRows]);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Filter by product
  useEffect(() => {
    if (!selectedProduct) {
      setFilteredData(rowData);
    } else {
      const pid = parseInt(selectedProduct, 10);
      setFilteredData(rowData.filter((r) => r.product_id === pid));
    }
  }, [rowData, selectedProduct]);

  // Load sends when a row is selected
  useEffect(() => {
    if (!selectedRow) {
      setSendData([]);
      return;
    }
    if (selectedRow._type === "triggered") {
      setSendData(selectedRow.sends || []);
      return;
    }
    setSendsLoading(true);
    fetchBroadcastSends(selectedRow.id)
      .then(setSendData)
      .catch(console.error)
      .finally(() => setSendsLoading(false));
  }, [selectedRow]);

  const handleCancel = useCallback(async (id) => {
    setActionLoading(true);
    try {
      await cancelBroadcast(id);
      loadData();
      if (selectedRow?.id === id) setSelectedRow(null);
    } catch (err) {
      console.error(err);
      alert("Cancel failed: " + err.message);
    } finally {
      setActionLoading(false);
    }
  }, [loadData, selectedRow]);

  const columnDefs = useMemo(
    () => [
      { field: "name", headerName: "Name", width: 260, editable: false },
      { field: "_email_type_label", headerName: "Email Type", width: 170, editable: false },
      {
        field: "status",
        headerName: "Status",
        width: 150,
        editable: false,
        cellRenderer: StatusRenderer,
      },
      {
        headerName: "Schedule",
        width: 210,
        editable: false,
        valueGetter: (p) => {
          if (p.data._type === "triggered") {
            return p.data._description ? `On trigger \u2014 ${p.data._description}` : "On trigger";
          }
          return p.data._schedule;
        },
        cellStyle: (p) => p.data._type === "triggered" ? { color: "#a78bfa", fontStyle: "italic" } : null,
      },
      {
        field: "total_recipients",
        headerName: "Recipients",
        width: 100,
        editable: false,
        valueFormatter: (p) => p.value != null ? p.value : "\u2014",
      },
      {
        field: "sent_count",
        headerName: "Sent",
        width: 70,
        editable: false,
      },
      {
        field: "error_count",
        headerName: "Errors",
        width: 75,
        editable: false,
        cellStyle: (p) => p.value > 0 ? { color: "#ef4444", fontWeight: 600 } : null,
      },
      {
        headerName: "",
        width: 80,
        editable: false,
        sortable: false,
        filter: false,
        cellRenderer: (params) => {
          const b = params.data;
          if (b._type !== "broadcast" || b.status !== "pending") return null;
          return (
            <button
              onClick={(e) => { e.stopPropagation(); handleCancel(b.id); }}
              disabled={actionLoading}
              style={{
                padding: "2px 8px", fontSize: "12px",
                background: "#6b7280", color: "#fff", border: "none",
                borderRadius: "3px", cursor: "pointer",
              }}
            >
              Cancel
            </button>
          );
        },
      },
    ],
    [handleCancel, actionLoading]
  );

  const sendColumnDefs = useMemo(
    () => [
      { field: "to_email", headerName: "Recipient", width: 250, editable: false },
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
      { field: "resend_id", headerName: "Resend ID", width: 280, editable: false },
      { field: "error_message", headerName: "Error", width: 250, editable: false },
    ],
    []
  );

  const defaultColDef = useMemo(
    () => ({ sortable: true, resizable: true, filter: true }),
    []
  );

  const onRowClicked = useCallback((event) => {
    setSelectedRow(event.data);
  }, []);

  return (
    <div className="grid-container">
      <div className="insights-toolbar" style={{ gap: "12px" }}>
        <div>
          <label htmlFor="bc-course-filter">Course:</label>
          <select
            id="bc-course-filter"
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
          {loading ? "Loading..." : `${filteredData.length} email${filteredData.length !== 1 ? "s" : ""}`}
        </span>
      </div>

      <div className="grid-wrapper" style={{ height: selectedRow ? "280px" : undefined }}>
        <AgGridReact
          theme={darkTheme}
          rowData={filteredData}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          getRowId={useCallback((params) => params.data._id, [])}
          onRowClicked={onRowClicked}
          rowSelection="single"
        />
      </div>

      {selectedRow && (
        <div style={{ marginTop: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <h3 style={{ margin: 0, fontSize: "14px", color: "#d6d3d1" }}>
              {selectedRow.name} \u2014 {sendData.length} send{sendData.length !== 1 ? "s" : ""}
              {selectedRow.error_summary && (
                <span style={{ color: "#ef4444", marginLeft: "12px", fontWeight: 400 }}>
                  {selectedRow.error_summary.split("\n")[0]}
                </span>
              )}
            </h3>
            <button
              onClick={() => setSelectedRow(null)}
              style={{
                background: "none", border: "1px solid #292524", color: "#a8a29e",
                padding: "2px 10px", borderRadius: "3px", cursor: "pointer", fontSize: "12px",
              }}
            >
              Close
            </button>
          </div>
          <div className="grid-wrapper" style={{ height: "260px" }}>
            {sendsLoading ? (
              <div style={{ padding: "20px", color: "#a8a29e" }}>Loading sends...</div>
            ) : (
              <AgGridReact
                theme={darkTheme}
                rowData={sendData}
                columnDefs={sendColumnDefs}
                defaultColDef={defaultColDef}
                getRowId={useCallback((params) => String(params.data.id), [])}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
