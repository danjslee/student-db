import { useState, useEffect, useCallback, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { darkTheme } from "../gridTheme";
import { fetchProducts, updateProduct } from "../api";

export default function ProductsGrid() {
  const [rowData, setRowData] = useState([]);

  useEffect(() => {
    fetchProducts().then(setRowData).catch(console.error);
  }, []);

  const columnDefs = useMemo(
    () => [
      { field: "product_id", headerName: "Product ID", editable: true },
      { field: "product_name", headerName: "Product Name", editable: true },
      { field: "kit_tag", headerName: "Kit Tag", editable: true },
      { field: "enrollment_count", headerName: "Enrollment Count", editable: false },
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
      await updateProduct(id, { [field]: newValue });
    } catch (err) {
      console.error("Update failed, reverting:", err);
      event.data[field] = event.oldValue;
      event.api.refreshCells({ rowNodes: [event.node], columns: [field] });
    }
  }, []);

  return (
    <div className="grid-container">
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
    </div>
  );
}
