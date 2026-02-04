import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { AgGridReact } from "ag-grid-react";
import { darkTheme } from "../gridTheme";
import { fetchStudents, updateStudent } from "../api";

const PAGE_SIZE = 200;

export default function StudentsGrid() {
  const [rowData, setRowData] = useState([]);
  const [searchText, setSearchText] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [skip, setSkip] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const initialLoad = useRef(true);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchText), 300);
    return () => clearTimeout(timer);
  }, [searchText]);

  // Fetch data when debounced search changes (reset pagination)
  useEffect(() => {
    if (initialLoad.current) {
      initialLoad.current = false;
    }
    setSkip(0);
    setLoading(true);
    fetchStudents({ skip: 0, limit: PAGE_SIZE, search: debouncedSearch || undefined })
      .then((data) => {
        setRowData(data);
        setHasMore(data.length >= PAGE_SIZE);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [debouncedSearch]);

  const loadMore = useCallback(() => {
    const nextSkip = skip + PAGE_SIZE;
    setLoading(true);
    fetchStudents({ skip: nextSkip, limit: PAGE_SIZE, search: debouncedSearch || undefined })
      .then((data) => {
        setRowData((prev) => [...prev, ...data]);
        setSkip(nextSkip);
        setHasMore(data.length >= PAGE_SIZE);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [skip, debouncedSearch]);

  const columnDefs = useMemo(
    () => [
      { field: "student_number", headerName: "Student #", editable: false },
      { field: "first_name", headerName: "First Name", editable: true },
      { field: "last_name", headerName: "Last Name", editable: true },
      { field: "preferred_name", headerName: "Preferred Name", editable: true },
      { field: "email", headerName: "Email", editable: true },
      { field: "alternative_email", headerName: "Alt Email", editable: true },
      { field: "country", headerName: "Country", editable: true },
      { field: "timezone", headerName: "Timezone", editable: true },
      { field: "closest_city", headerName: "City", editable: true },
      {
        field: "dob",
        headerName: "DOB",
        editable: false,
        valueFormatter: (params) => {
          if (!params.value) return "";
          return new Date(params.value).toLocaleDateString();
        },
      },
      { field: "gender", headerName: "Gender", editable: true },
      { field: "learn_about_course", headerName: "How They Heard", editable: true },
      { field: "consent_images", headerName: "Consent Images", editable: false },
      { field: "consent_photo_on_site", headerName: "Consent Photo", editable: false },
      { field: "what_made_you_join", headerName: "Why Join", editable: true },
      { field: "get_from", headerName: "Get From", editable: true },
      { field: "here_for", headerName: "Here For", editable: true },
      { field: "claude_confidence_level", headerName: "Confidence Level", editable: false },
      {
        field: "onboarding_date",
        headerName: "Onboarding Date",
        editable: false,
        valueFormatter: (params) => {
          if (!params.value) return "";
          return new Date(params.value).toLocaleDateString();
        },
      },
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
      await updateStudent(id, { [field]: newValue });
    } catch (err) {
      console.error("Update failed, reverting:", err);
      event.data[field] = event.oldValue;
      event.api.refreshCells({ rowNodes: [event.node], columns: [field] });
    }
  }, []);

  return (
    <div className="grid-container">
      <div className="search-bar">
        <input
          className="search-input"
          type="text"
          placeholder="Search students..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
        />
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
