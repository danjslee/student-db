import { useState, useEffect, useCallback, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { darkTheme } from "../gridTheme";
import { fetchEnrollments, fetchProducts, updateEnrollment } from "../api";

const PAGE_SIZE = 200;

export default function EnrollmentsGrid() {
  const [rowData, setRowData] = useState([]);
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState("");

  useEffect(() => {
    fetchProducts().then(setProducts).catch(console.error);
  }, []);

  useEffect(() => {
    setSkip(0);
    setLoading(true);
    const product_id = selectedProduct || undefined;
    fetchEnrollments({ skip: 0, limit: PAGE_SIZE, product_id })
      .then((data) => {
        setRowData(data);
        setHasMore(data.length >= PAGE_SIZE);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedProduct]);

  const loadMore = useCallback(() => {
    const nextSkip = skip + PAGE_SIZE;
    setLoading(true);
    const product_id = selectedProduct || undefined;
    fetchEnrollments({ skip: nextSkip, limit: PAGE_SIZE, product_id })
      .then((data) => {
        setRowData((prev) => [...prev, ...data]);
        setSkip(nextSkip);
        setHasMore(data.length >= PAGE_SIZE);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [skip, selectedProduct]);

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
      // Survey columns
      { field: "biggest_win", headerName: "Biggest Win", editable: false },
      { field: "three_things_learned", headerName: "Three Things Learned", editable: false },
      { field: "confidence_after", headerName: "Confidence (Post)", editable: false },
      { field: "satisfaction", headerName: "Satisfaction", editable: false },
      { field: "recommend_score", headerName: "NPS Score", editable: false },
      { field: "testimonial", headerName: "Testimonial", editable: false },
      { field: "improvement_suggestion", headerName: "Improvement Suggestion", editable: false },
      { field: "interest_longer_program", headerName: "Interest in Longer Program", editable: false },
      { field: "followup_topics", headerName: "Follow-up Topics", editable: false },
      { field: "beginner_friendly_rating", headerName: "Beginner Rating", editable: false },
      { field: "expected_learning_not_covered", headerName: "Expected Not Covered", editable: false },
      { field: "anything_else", headerName: "Anything Else", editable: false },
      {
        field: "survey_submit_date",
        headerName: "Survey Submit Date",
        editable: false,
        valueFormatter: (params) => {
          if (!params.value) return "";
          return new Date(params.value).toLocaleDateString();
        },
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
      <div className="insights-toolbar">
        <label htmlFor="course-filter">Course:</label>
        <select
          id="course-filter"
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
