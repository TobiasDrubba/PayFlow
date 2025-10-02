import React, { useState, useMemo } from "react";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { DragDropContext, Droppable, Draggable } from "@hello-pangea/dnd";
import {
  Box,
  Typography,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  TextField,
  InputAdornment,
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Menu,
  MenuItem,
} from "@mui/material";
import { Search as SearchIcon, Upload as UploadIcon, Settings as SettingsIcon, Close as CloseIcon } from "@mui/icons-material";
import { fetchAggregation, fetchSumsForRanges, deletePayments } from "./api";
import "./PaymentsTable.css";

// Custom hooks
import { usePayments } from "./hooks/usePayments";
import { useCategories } from "./hooks/useCategories";
import { useTableColumns } from "./hooks/useTableColumns";

// Components
import ManageCategoriesDialog from "./components/ManageCategoriesDialog";
import SummaryCards from "./components/SummaryCards";
import PaymentTableRow from "./components/PaymentTableRow";
import AggregationDialog from "./components/AggregationDialog";
import FileUpload from "./components/FileUpload";
import SettingsDialog from "./components/SettingsDialog";

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

  const [summarySums, setSummarySums] = useState({
    total: 0,
    month: 0,
    past7: 0,
    past30: 0,
    past90: 0,
    custom: 0,
  });

  // Dialog states
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false);

  // Selection state
  const [selectedIds, setSelectedIds] = useState([]);
  const [contextMenu, setContextMenu] = useState(null);

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

  // Find newest payment date for summary cards reference
  const newestPaymentDate = React.useMemo(() => {
    if (!payments.length) return null;
    return payments.reduce((latest, p) => {
      const d = new Date(p.date);
      return (!latest || d > latest) ? d : latest;
    }, null);
  }, [payments]);

  // Handler for summary card aggregation
  const handleSummaryCardAggregate = async ({ type, start, end }) => {
    let title = "";
    if (type === "total") {
      title = "Total Aggregation";
    } else if (type === "past7") {
      title = "Past 7 Days Aggregation";
    } else if (type === "past30") {
      title = "Past 30 Days Aggregation";
    } else if (type === "custom") {
      title = "Custom Range Aggregation";
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

  const handleUploadSuccess = () => {
    refetchPayments();
    setUploadDialogOpen(false);
  };

  React.useEffect(() => {
    if (!payments.length) return;
    // Use newest payment date as reference for summary cards (except total/custom)
    const newest = payments.reduce((latest, p) => {
      const d = new Date(p.date);
      return (!latest || d > latest) ? d : latest;
    }, null);

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

    // Use newest payment date as "now" for relative ranges
    const nowDate = newest;
    const ranges = {
      total: { start: null, end: null },
      past7: { start: toNaiveISOString(new Date(nowDate.getTime() - 6 * 24 * 60 * 60 * 1000)), end: toNaiveISOString(nowDate) },
      past30: { start: toNaiveISOString(new Date(nowDate.getTime() - 29 * 24 * 60 * 60 * 1000)), end: toNaiveISOString(nowDate) },
    };
    fetchSumsForRanges(ranges)
      .then(setSummarySums)
      .catch(() => {});
  }, [payments, dateRange]);

  // Handle row selection
  const handleRowClick = (payment, event) => {
    if (event.ctrlKey || event.metaKey) {
      setSelectedIds((prev) =>
        prev.includes(payment.id)
          ? prev.filter((id) => id !== payment.id)
          : [...prev, payment.id]
      );
    } else if (event.shiftKey && selectedIds.length > 0) {
      const lastIndex = filteredPayments.findIndex((p) => p.id === selectedIds[selectedIds.length - 1]);
      const thisIndex = filteredPayments.findIndex((p) => p.id === payment.id);
      if (lastIndex !== -1 && thisIndex !== -1) {
        const [start, end] = [lastIndex, thisIndex].sort((a, b) => a - b);
        const rangeIds = filteredPayments.slice(start, end + 1).map((p) => p.id);
        setSelectedIds(Array.from(new Set([...selectedIds, ...rangeIds])));
      }
    } else {
      setSelectedIds([payment.id]);
    }
  };

  // Context menu handlers
  const handleRowContextMenu = (payment, event) => {
    event.preventDefault();
    if (!selectedIds.includes(payment.id)) {
      setSelectedIds([payment.id]);
    }
    setContextMenu(
      contextMenu === null
        ? { mouseX: event.clientX - 2, mouseY: event.clientY - 4 }
        : null
    );
  };

  const handleCloseContextMenu = () => {
    setContextMenu(null);
  };

  const handleDeleteSelected = async () => {
    handleCloseContextMenu();
    if (selectedIds.length === 0) return;
    if (!window.confirm(`Delete ${selectedIds.length} selected payment(s)?`)) return;
    try {
      await deletePayments(selectedIds);
      setSelectedIds([]);
      refetchPayments();
    } catch (e) {
      alert("Failed to delete payments.");
    }
  };

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

      {/* Upload Dialog */}
      <Dialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: '20px',
            boxShadow: '0 12px 48px rgba(0,0,0,0.12)',
          }
        }}
      >
        <DialogTitle sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          pb: 2,
          borderBottom: '1px solid rgba(0,0,0,0.06)',
        }}>
          <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: -0.01 }}>
            Upload Payment Files
          </Typography>
          <IconButton onClick={() => setUploadDialogOpen(false)} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ pt: 3 }}>
          <FileUpload onSuccess={handleUploadSuccess} />
        </DialogContent>
      </Dialog>

      {/* Settings Dialog */}
      <SettingsDialog
        open={settingsDialogOpen}
        onClose={() => setSettingsDialogOpen(false)}
        setManagerOpen={setManagerOpen}
        dateRange={dateRange}
        setDateRange={setDateRange}
        orderedColumns={orderedColumns}
        visibleColumns={visibleColumns}
        toggleColumn={toggleColumn}
        categories={categories}
        refetchPayments={refetchPayments}
      />

      <div className="payments-container animate-in">
        {/* Header */}
        <div className="page-header">
          <div className="header-content">
            <h1>Payment Overview</h1>
            <p>Track your transactions with a refined, modern interface</p>
          </div>
          <div className="header-actions">
            <Button
              variant="contained"
              className="btn-primary upload-btn"
              onClick={() => setSettingsDialogOpen(true)}
              startIcon={<SettingsIcon />}
            >
              Settings
            </Button>
          </div>
        </div>

        {/* Summary Cards */}
        <SummaryCards
          totalSum={summarySums.total}
          customSum={summarySums.custom}
          dateRange={dateRange}
          onAggregate={handleSummaryCardAggregate}
          past7DaysSum={summarySums.past7}
          past30DaysSum={summarySums.past30}
          newestPaymentDate={newestPaymentDate}
        />

        {/* Search Bar and Upload Button */}
        <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
          <TextField
            fullWidth
            placeholder="Search transactions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ color: 'rgba(0,0,0,0.4)' }} />
                </InputAdornment>
              ),
              sx: {
                borderRadius: '12px',
                background: 'white',
                '& .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'rgba(0,0,0,0.08)',
                  borderWidth: '2px',
                },
                '&:hover .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'rgba(102,126,234,0.3)',
                },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                  borderColor: '#667eea',
                },
                height: '48px',
                fontSize: '15px',
                fontWeight: 500,
              }
            }}
          />
          <Button
            variant="contained"
            startIcon={<UploadIcon />}
            onClick={() => setUploadDialogOpen(true)}
            className="btn-primary upload-btn"
          >
            Upload
          </Button>
        </Box>

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
                      selected={selectedIds.includes(payment.id)}
                      onRowClick={handleRowClick}
                      onRowContextMenu={handleRowContextMenu}
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
        {/* Context Menu for Delete */}
        <Menu
          open={contextMenu !== null}
          onClose={handleCloseContextMenu}
          anchorReference="anchorPosition"
          anchorPosition={
            contextMenu !== null
              ? { top: contextMenu.mouseY, left: contextMenu.mouseX }
              : undefined
          }
        >
          <MenuItem onClick={handleDeleteSelected} disabled={selectedIds.length === 0}>
            Delete {selectedIds.length > 1 ? "Selected Payments" : "Payment"}
          </MenuItem>
        </Menu>
      </div>
    </LocalizationProvider>
  );
}