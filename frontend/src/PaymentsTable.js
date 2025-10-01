import React, { useState, useMemo } from "react";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { DragDropContext, Droppable, Draggable } from "@hello-pangea/dnd";
import {
  Typography,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
} from "@mui/material";
import { fetchAggregation, fetchSumsForRanges } from "./api";
import "./PaymentsTable.css";

// Custom hooks
import { usePayments } from "./hooks/usePayments";
import { useCategories } from "./hooks/useCategories";
import { useTableColumns } from "./hooks/useTableColumns";

// Components
import ManageCategoriesDialog from "./components/ManageCategoriesDialog";
import SummaryCards from "./components/SummaryCards";
import TableControls from "./components/TableControls";
import PaymentTableRow from "./components/PaymentTableRow";
import AggregationDialog from "./components/AggregationDialog";
import FileUpload from "./components/FileUpload";

export default function PaymentsTable() {
  const { payments, setPayments, loading, error, refetchPayments } = usePayments();
  const [search, setSearch] = useState("");
  const [dateRange, setDateRange] = useState([null, null]);

  const {
    categories,
    categoryTree,
    managerOpen,
    setManagerOpen,
    handleUpdateCategoryTree,
    handleCategoryChange
  } = useCategories(refetchPayments);

  const {
    orderedColumns,
    visibleColumns,
    toggleColumn,
    onDragEnd
  } = useTableColumns();

  const now = useMemo(() => new Date(), []);

  const [summarySums, setSummarySums] = useState({
    total: 0,
    month: 0,
    past7: 0,
    past30: 0,
    past90: 0,
    custom: 0,
  });

  // Filter payments by search term
  const filteredPayments = useMemo(() => {
    if (!search) return payments;
    const term = search.toLowerCase();
    return payments.filter(p =>
      Object.values(p).some(val =>
        (val ?? "").toString().toLowerCase().includes(term)
      )
    );
  }, [payments, search]);

  const handleCategoryChangeWithDialog = (payment, value) => {
    handleCategoryChange(payment, value, payments, setPayments);
  };

  // Aggregation dialog state
  const [aggregationOpen, setAggregationOpen] = useState(false);
  const [aggregationData, setAggregationData] = useState(null);
  const [aggregationLoading, setAggregationLoading] = useState(false);
  const [aggregationError, setAggregationError] = useState("");
  const [aggregationTitle, setAggregationTitle] = useState("");

  // Handler for summary card click
  const handleSummaryCardClick = async (type) => {
    let start = null, end = null, title = "";
    if (type === "total") {
      title = "Total Aggregation";
    } else if (type === "month") {
      title = "Monthly Aggregation";
      start = new Date(now.getFullYear(), now.getMonth(), 1);
      end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    } else if (type === "custom") {
      title = "Custom Range Aggregation";
      start = dateRange[0];
      end = dateRange[1];
      if (!start || !end) return;
    }
    setAggregationTitle(title);
    setAggregationLoading(true);
    setAggregationOpen(true);
    setAggregationError("");
    try {
      const params = {};
      if (start) params.start_date = start.toISOString();
      if (end) params.end_date = end.toISOString();
      const data = await fetchAggregation(params);
      setAggregationData(data);
    } catch (err) {
      setAggregationError("Failed to fetch aggregation data.");
      setAggregationData(null);
    }
    setAggregationLoading(false);
  };

  React.useEffect(() => {
    if (!payments.length) return;
    const nowDate = new Date();
    const toNaiveISOString = (d) => d ? d.toISOString().slice(0, 19) : null;

    if (dateRange[0] && dateRange[1]) {
      const ranges = {
        custom: {
          start: toNaiveISOString(dateRange[0]),
          end: toNaiveISOString(dateRange[1]),
        }
      };
      fetchSumsForRanges(ranges)
        .then((res) => setSummarySums((prev) => ({
          ...prev,
          custom: res.custom ?? 0
        })))
        .catch(() => {});
      return;
    }

    const ranges = {
      total: { start: null, end: null },
      past7: { start: toNaiveISOString(new Date(nowDate.getTime() - 6 * 24 * 60 * 60 * 1000)), end: toNaiveISOString(nowDate) },
      past30: { start: toNaiveISOString(new Date(nowDate.getTime() - 29 * 24 * 60 * 60 * 1000)), end: toNaiveISOString(nowDate) },
    };
    fetchSumsForRanges(ranges)
      .then(setSummarySums)
      .catch(() => {});
  }, [payments, dateRange]);

  if (loading) {
    return (
      <div className="payments-container">
        <div className="loading-container">
          <div className="loading-spinner">
            <CircularProgress size={64} thickness={3.5} sx={{ color: '#667eea' }} />
          </div>
          <Typography className="loading-text">
            Preparing your beautiful dashboard…
          </Typography>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="payments-container">
        <Typography color="error" sx={{ textAlign: 'center', mt: 4 }}>{error}</Typography>
      </div>
    );
  }

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <ManageCategoriesDialog
        open={managerOpen}
        onClose={() => setManagerOpen(false)}
        categoryTree={categoryTree}
        onUpdate={handleUpdateCategoryTree}
        payments={payments}
      />
      <AggregationDialog
        open={aggregationOpen}
        onClose={() => setAggregationOpen(false)}
        data={aggregationData}
        loading={aggregationLoading}
        error={aggregationError}
        title={aggregationTitle}
      />

      <div className="payments-container animate-in">
        {/* Header */}
        <div className="page-header">
          <div className="header-content">
            <h1>Payments Overview</h1>
            <p>Track your transactions with a refined, modern interface</p>
          </div>
          <div className="header-actions">
            <TableControls
              search={search}
              setSearch={setSearch}
              dateRange={dateRange}
              setDateRange={setDateRange}
              orderedColumns={orderedColumns}
              visibleColumns={visibleColumns}
              toggleColumn={toggleColumn}
            />
            <Button
              className="btn-secondary"
              onClick={() => setManagerOpen(true)}
              sx={{
                textTransform: 'none',
                fontWeight: 600,
                height: '44px',
                px: 3,
              }}
            >
              Manage Categories
            </Button>
          </div>
        </div>

        {/* Summary Cards */}
        <SummaryCards
          totalSum={summarySums.total}
          customSum={summarySums.custom}
          now={now}
          dateRange={dateRange}
          onCardClick={handleSummaryCardClick}
          past7DaysSum={summarySums.past7}
          past30DaysSum={summarySums.past30}
        />

        {/* File Upload UI */}
        <div className="file-upload-section">
          <FileUpload onSuccess={refetchPayments} />
        </div>

        {/* Table */}
        <div className="table-container animate-in">
          <div className="table-header">
            <h2>Transactions</h2>
            <span className="table-count">
              {filteredPayments.length} {filteredPayments.length === 1 ? 'item' : 'items'}
            </span>
          </div>

          <TableContainer sx={{ maxHeight: "65vh" }}>
            <DragDropContext onDragEnd={onDragEnd}>
              <Table className="payments-table" stickyHeader size="medium" aria-label="payments table">
                <TableHead>
                  <Droppable droppableId="columns" direction="horizontal">
                    {(provided) => (
                      <TableRow ref={provided.innerRef} {...provided.droppableProps}>
                        {orderedColumns.map((col, index) => {
                          if (!visibleColumns.has(col.id)) return null;
                          return (
                            <Draggable draggableId={col.id} index={index} key={col.id}>
                              {(dragProvided, snapshot) => (
                                <TableCell
                                  align={col.align}
                                  ref={dragProvided.innerRef}
                                  {...dragProvided.draggableProps}
                                  {...dragProvided.dragHandleProps}
                                  className={snapshot.isDragging ? 'dragging' : ''}
                                  sx={{
                                    cursor: snapshot.isDragging ? 'grabbing' : 'grab',
                                    '&:hover': {
                                      background: 'rgba(102,126,234,0.08)',
                                      color: '#667eea',
                                    }
                                  }}
                                >
                                  {col.label}
                                </TableCell>
                              )}
                            </Draggable>
                          );
                        })}
                        {provided.placeholder}
                      </TableRow>
                    )}
                  </Droppable>
                </TableHead>
                <TableBody>
                  {filteredPayments.map((payment) => (
                    <PaymentTableRow
                      key={payment.id}
                      payment={payment}
                      orderedColumns={orderedColumns}
                      visibleColumns={visibleColumns}
                      categories={categories}
                      onCategoryChange={handleCategoryChangeWithDialog}
                    />
                  ))}
                  {filteredPayments.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={visibleColumns.size || 1} className="empty-state">
                        <div className="empty-state-icon">📭</div>
                        <div className="empty-state-text">No results found. Try adjusting your filters.</div>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </DragDropContext>
          </TableContainer>
        </div>
      </div>
    </LocalizationProvider>
  );
}