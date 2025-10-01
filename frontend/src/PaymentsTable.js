import React, { useState, useMemo } from "react";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { DragDropContext, Droppable, Draggable } from "@hello-pangea/dnd";
import {
  Box,
  Typography,
  Stack,
  CircularProgress,
  Paper,
  Chip,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
} from "@mui/material";
import { fetchAggregation, fetchSumsForRanges, uploadPaymentFiles } from "./api";

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

  // Replace handleCategoryChangeWithDialog with direct call
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

    // If custom date range is set, only fetch for custom
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

    // Otherwise, fetch for the default cards only
    const ranges = {
      total: { start: null, end: null },
      past7: { start: toNaiveISOString(new Date(nowDate.getTime() - 6 * 24 * 60 * 60 * 1000)), end: toNaiveISOString(nowDate) },
      past30: { start: toNaiveISOString(new Date(nowDate.getTime() - 29 * 24 * 60 * 60 * 1000)), end: toNaiveISOString(nowDate) },
    };
    fetchSumsForRanges(ranges)
      .then(setSummarySums)
      .catch(() => {});
  }, [payments, dateRange]);

  // File upload state
  const [uploadFiles, setUploadFiles] = useState([]); // [{file, type}]
  const [uploadError, setUploadError] = useState("");
  const [uploading, setUploading] = useState(false);

  // PaymentSource options (excluding "Other")
    /*
    class PaymentSource(Enum):
    ALIPAY = "Alipay"
    WECHAT = "WeChat"
    TSINGHUA_CARD = "Tsinghua Card"
     */
  const paymentSourceOptions = [
    { value: "Alipay", label: "Alipay" },
    { value: "WeChat", label: "WeChat" },
    { value: "Tsinghua Card", label: "Tsinghua Card" },
  ];

  const handleFileChange = (e) => {
    setUploadError("");
    const files = Array.from(e.target.files).slice(0, 3);
    setUploadFiles(files.map(file => ({ file, type: "" })));
  };

  const handleTypeChange = (idx, type) => {
    setUploadFiles(files =>
      files.map((f, i) => (i === idx ? { ...f, type } : f))
    );
  };

  const handleUpload = async () => {
    setUploadError("");
    if (!uploadFiles.length) {
      setUploadError("Please select up to 3 files.");
      return;
    }
    if (uploadFiles.some(f => !f.type)) {
      setUploadError("Please select a type for each file.");
      return;
    }
    setUploading(true);
    try {
      await uploadPaymentFiles(uploadFiles);
      setUploadFiles([]);
      setUploadError("");
      refetchPayments();
    } catch (err) {
      setUploadError(err.message || "Upload failed");
    }
    setUploading(false);
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh" }}>
        <Stack spacing={2} alignItems="center">
          <CircularProgress size={56} thickness={4} />
          <Typography variant="h6" sx={{ letterSpacing: 0.4, opacity: 0.8 }}>
            Preparing your beautiful dashboard…
          </Typography>
        </Stack>
      </Box>
    );
  }

  if (error) return <Typography color="error">{error}</Typography>;

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

      <Box
        sx={{
          maxWidth: "1200px",
          margin: "40px auto",
          px: { xs: 2, md: 0 },
          fontFamily: `"Inter", "SF Pro Display", "Segoe UI", Roboto, Arial, sans-serif`,
        }}
      >
        {/* Header */}
        <Box
          sx={{
            mb: 3,
            display: "flex",
            alignItems: { xs: "flex-start", md: "center" },
            justifyContent: "space-between",
            flexDirection: { xs: "column", md: "row" },
            gap: 2,
          }}
        >
          <Box>
            <Typography
              variant="h4"
              sx={{
                fontWeight: 800,
                letterSpacing: -0.5,
                lineHeight: 1.2,
              }}
            >
              Payments Overview
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Track your transactions with a refined, modern interface.
            </Typography>
          </Box>
          <Stack direction="row" spacing={2}>
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
              variant="contained"
              color="secondary"
              onClick={() => setManagerOpen(true)}
              sx={{ height: 40, alignSelf: "center" }}
            >
              Manage Categories
            </Button>
          </Stack>
        </Box>

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
        <Box sx={{ mb: 2 }}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center">
            <input
              type="file"
              multiple
              accept=".csv,.xls,.xlsx"
              style={{ display: "none" }}
              id="file-upload"
              onChange={handleFileChange}
              disabled={uploading}
            />
            <label htmlFor="file-upload">
              <Button variant="outlined" component="span" disabled={uploading}>
                Select Files (max 3)
              </Button>
            </label>
            {uploadFiles.map((f, idx) => (
              <Stack key={f.file.name} direction="row" spacing={1} alignItems="center">
                <Typography>{f.file.name}</Typography>
                <select
                  value={f.type}
                  onChange={e => handleTypeChange(idx, e.target.value)}
                  disabled={uploading}
                  style={{ height: 32 }}
                >
                  <option value="">Select Type</option>
                  {paymentSourceOptions.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </Stack>
            ))}
            <Button
              variant="contained"
              color="primary"
              onClick={handleUpload}
              disabled={uploading || !uploadFiles.length || uploadFiles.some(f => !f.type)}
            >
              {uploading ? "Uploading..." : "Upload"}
            </Button>
            {uploadError && (
              <Typography color="error" sx={{ ml: 2 }}>
                {uploadError}
              </Typography>
            )}
          </Stack>
        </Box>

        {/* Table */}
        <Paper
          elevation={0}
          sx={{
            borderRadius: 3,
            overflow: "hidden",
            bgcolor: "background.paper",
            border: (theme) => `1px solid ${theme.palette.divider}`,
          }}
        >
          <Box
            sx={{
              px: 3,
              py: 2,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: "linear-gradient(180deg, rgba(0,0,0,0.02), rgba(0,0,0,0))",
            }}
          >
            <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: 0.2 }}>
              Transactions
            </Typography>
            <Chip
              size="small"
              label={`${filteredPayments.length} items`}
              color="default"
              variant="outlined"
              sx={{ borderRadius: 2 }}
            />
          </Box>
          <Divider />

          <TableContainer sx={{ maxHeight: "65vh" }}>
            <DragDropContext onDragEnd={onDragEnd}>
              <Table stickyHeader size="medium" aria-label="payments table">
                <TableHead
                  sx={{
                    "& .MuiTableCell-head": {
                      bgcolor: "background.default",
                      color: "text.secondary",
                      fontWeight: 700,
                      letterSpacing: 0.4,
                      borderBottom: (t) => `1px solid ${t.palette.divider}`,
                    },
                  }}
                >
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
                                  sx={{
                                    cursor: "grab",
                                    opacity: snapshot.isDragging ? 0.7 : 1,
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
                <TableBody
                  sx={{
                    "& .MuiTableRow-root:hover": {
                      background: "linear-gradient(90deg, rgba(99,102,241,0.06), rgba(99,102,241,0.00))",
                    },
                    "& .MuiTableCell-body": {
                      borderBottom: (t) => `1px dashed ${t.palette.divider}`,
                    },
                  }}
                >
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
                      <TableCell colSpan={visibleColumns.size || 1} align="center" sx={{ py: 6, color: "text.secondary" }}>
                        No results. Try adjusting filters.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </DragDropContext>
          </TableContainer>
        </Paper>
      </Box>
    </LocalizationProvider>
  );
}

