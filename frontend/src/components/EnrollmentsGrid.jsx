import { useState, useEffect, useCallback, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { themeAlpine } from "ag-grid-community";
import { fetchEnrollments, updateEnrollment } from "../api";

const PAGE_SIZE = 200;

export default function EnrollmentsGrid() {
  const [rowData, setRowData] = useState([]);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchEnrollments({ skip: 0, limit: PAGE_SIZE })
      .then((data) => {
        setRowData(data);
        setHasMore(data.length >= PAGE_SIZE);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const loadMore = useCallback(() => {
    const nextSkip = skip + PAGE_SIZE;
    setLoading(true);
    fetchEnrollments({ skip: nextSkip, limit: PAGE_SIZE })
      .then((data) => {
        setRowData((prev) => [...prev, ...data]);
        setSkip(nextSkip);
        setHasMore(data.length >= PAGE_SIZE);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [skip]);

  const columnDefs = useMemo(
    () => [
      { field: "enrollment_id", headerName: "Enrollment ID", editable: false },
      { field: "status", headerName: "Status", editable: true },
      {
        headerName: "Student Name",
        editable: false,
        valueGetter: (params) => {
          const s = params.data.student;
          return s ? `${s.first_name} ${s.last_name}` : "";
        },
      },
      {
        headerName: "Student Email",
        editable: false,
        valueGetter: (params) => params.data.student?.email || "",
      },
      {
        headerName: "Product Name",
        editable: false,
        valueGetter: (params) => params.data.product?.product_name || "",
      },
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
      await updateEnrollment(id, { [field]: newValue });
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
          theme={themeAlpine}
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
