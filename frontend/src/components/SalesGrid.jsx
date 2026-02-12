import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { AgGridReact } from "ag-grid-react";
import { darkTheme } from "../gridTheme";
import { fetchSales, fetchProducts, updateSale, importSalesCSV } from "../api";

const PAGE_SIZE = 200;

function formatCents(cents) {
  if (cents == null) return "";
  return `$${(cents / 100).toFixed(2)}`;
}

export default function SalesGrid() {
  const [rowData, setRowData] = useState([]);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [importProduct, setImportProduct] = useState("");
  const [importStatus, setImportStatus] = useState(null);
  const fileRef = useRef(null);

  useEffect(() => {
    fetchProducts().then(setProducts).catch(console.error);
  }, []);

  const loadData = useCallback((prodId, startSkip = 0) => {
    setLoading(true);
    const product_id = prodId || undefined;
    fetchSales({ skip: startSkip, limit: PAGE_SIZE, product_id })
      .then((data) => {
        if (startSkip === 0) {
          setRowData(data);
        } else {
          setRowData((prev) => [...prev, ...data]);
        }
        setSkip(startSkip);
        setHasMore(data.length >= PAGE_SIZE);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadData(selectedProduct, 0);
  }, [selectedProduct, loadData]);

  const loadMore = useCallback(() => {
    loadData(selectedProduct, skip + PAGE_SIZE);
  }, [skip, selectedProduct, loadData]);

  const handleImport = useCallback(async () => {
    const file = fileRef.current?.files?.[0];
    if (!file || !importProduct) return;
    setImportStatus("Importing...");
    try {
      const result = await importSalesCSV(importProduct, file);
      setImportStatus(
        `Created: ${result.created}, Skipped: ${result.skipped}, Linked: ${result.linked}` +
        (result.errors.length ? ` | Errors: ${result.errors.length}` : "")
      );
      loadData(selectedProduct, 0);
    } catch (err) {
      setImportStatus(`Error: ${err.message}`);
    }
    if (fileRef.current) fileRef.current.value = "";
  }, [importProduct, selectedProduct, loadData]);

  const columnDefs = useMemo(
    () => [
      { field: "sale_id", headerName: "Sale ID", editable: false, width: 280 },
      { field: "buyer_email", headerName: "Buyer Email", editable: false, width: 220 },
      { field: "buyer_name", headerName: "Buyer Name", editable: false, width: 160 },
      {
        headerName: "Product",
        editable: false,
        width: 160,
        valueGetter: (p) => p.data.product?.product_name || "",
      },
      {
        field: "amount_cents",
        headerName: "Amount",
        editable: false,
        width: 100,
        valueFormatter: (p) => formatCents(p.value),
      },
      { field: "currency", headerName: "Cur", editable: false, width: 60 },
      { field: "quantity", headerName: "Qty", editable: false, width: 60 },
      { field: "status", headerName: "Status", editable: true, width: 110 },
      { field: "source", headerName: "Source", editable: false, width: 80 },
      {
        field: "purchase_date",
        headerName: "Purchase Date",
        editable: false,
        width: 130,
        valueFormatter: (p) => {
          if (!p.value) return "";
          return new Date(p.value).toLocaleDateString();
        },
      },
      { field: "notes", headerName: "Notes", editable: true, width: 200 },
    ],
    []
  );

  const defaultColDef = useMemo(
    () => ({ sortable: true, resizable: true, filter: true }),
    []
  );

  const getRowId = useCallback((params) => String(params.data.id), []);

  const onCellValueChanged = useCallback(async (event) => {
    const { id } = event.data;
    const field = event.colDef.field;
    const newValue = event.newValue;
    try {
      await updateSale(id, { [field]: newValue });
    } catch (err) {
      console.error("Update failed, reverting:", err);
      event.data[field] = event.oldValue;
      event.api.refreshCells({ rowNodes: [event.node], columns: [field] });
    }
  }, []);

  return (
    <div className="grid-container">
      <div className="insights-toolbar" style={{ flexWrap: "wrap", gap: "12px" }}>
        <div>
          <label htmlFor="sales-course-filter">Course:</label>
          <select
            id="sales-course-filter"
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
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <label>Import CSV:</label>
          <select
            value={importProduct}
            onChange={(e) => setImportProduct(e.target.value)}
            style={{ minWidth: "120px" }}
          >
            <option value="">Select product</option>
            {products.map((p) => (
              <option key={p.product_id} value={p.product_id}>
                {p.product_name}
              </option>
            ))}
          </select>
          <input type="file" accept=".csv" ref={fileRef} />
          <button onClick={handleImport} disabled={!importProduct || loading}>
            Import
          </button>
          {importStatus && (
            <span style={{ fontSize: "0.85em", opacity: 0.8 }}>{importStatus}</span>
          )}
        </div>
      </div>
      <div className="grid-wrapper">
        <AgGridReact
          theme={darkTheme}
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          getRowId={getRowId}
          onCellValueChanged={onCellValueChanged}
        />
      </div>
      {hasMore && (
        <div className="load-more-wrapper">
          <button className="load-more-btn" onClick={loadMore} disabled={loading}>
            {loading ? "Loading..." : "Load More"}
          </button>
        </div>
      )}
    </div>
  );
}
