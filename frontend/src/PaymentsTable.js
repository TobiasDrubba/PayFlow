import React, { useEffect, useState, useMemo } from "react";
import { fetchPayments } from "./api";
import {
  Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Paper, CircularProgress, Typography, TextField,
  Box, Grid, Card, CardContent, Chip, Avatar, Stack, Tooltip, Divider,
  Menu, MenuItem, Checkbox, ListItemText, Button
} from "@mui/material";
import { DateRangePicker } from "@mui/x-date-pickers-pro/DateRangePicker";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { format, isWithinInterval, startOfMonth, endOfMonth } from "date-fns";
import { DragDropContext, Droppable, Draggable } from "@hello-pangea/dnd";
export default function PaymentsTable() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [dateRange, setDateRange] = useState([null, null]);
  // Column visibility + order
  const allColumns = useMemo(() => ([
    { id: "date", label: "Date" },
    { id: "amount", label: "Amount", align: "right" },
    { id: "currency", label: "Currency" },
    { id: "merchant", label: "Merchant" },
    { id: "auto_category", label: "Auto Category" },
    { id: "source", label: "Source" },
    { id: "type", label: "Type" },
    { id: "note", label: "Note" },
    { id: "cust_category", label: "Custom Category" },
  ]), []);
  const [columnOrder, setColumnOrder] = useState(() => {
    const saved = localStorage.getItem("paymentsTable.columnOrder");
    return saved ? JSON.parse(saved) : allColumns.map(c => c.id);
  });
  const [visibleColumns, setVisibleColumns] = useState(() => {
    const saved = localStorage.getItem("paymentsTable.visibleColumns");
    return new Set(saved ? JSON.parse(saved) : allColumns.map(c => c.id));
  });
  useEffect(() => {
    localStorage.setItem("paymentsTable.columnOrder", JSON.stringify(columnOrder));
  }, [columnOrder]);
  useEffect(() => {
    localStorage.setItem("paymentsTable.visibleColumns", JSON.stringify(Array.from(visibleColumns)));
  }, [visibleColumns]);
  const orderedColumns = useMemo(
    () => columnOrder.map(id => allColumns.find(c => c.id === id)).filter(Boolean),
    [columnOrder, allColumns]
  );

  useEffect(() => {
    fetchPayments()
      .then(data => setPayments(data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

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

    // --- Sum Calculations ---
    const isPositive = (t) => t === "income" || t === "refund";
    const isAbort = (t) => t === "abort";

    const totalSum = useMemo(
      () =>
        payments.reduce((sum, p) => {
          const t = p.type?.toLowerCase();
          if (isAbort(t)) return sum;
          const sign = isPositive(t) ? 1 : -1;
          return sum + sign * (Math.abs(p.amount) || 0);
        }, 0),
      [payments]
    );
  const now = useMemo(() => new Date(), []);
    const monthlySum = useMemo(
      () =>
        payments
          .filter(p =>
            !isAbort(p.type?.toLowerCase()) &&
            isWithinInterval(new Date(p.date), {
              start: startOfMonth(now),
              end: endOfMonth(now),
            })
          )
          .reduce((sum, p) => {
            const t = p.type?.toLowerCase();
            const sign = isPositive(t) ? 1 : -1;
            return sum + sign * (Math.abs(p.amount) || 0);
          }, 0),
      [payments, now]
    );

    const customSum = useMemo(() => {
      if (!dateRange[0] || !dateRange[1]) return 0;
      return payments
        .filter(p =>
          !isAbort(p.type?.toLowerCase()) &&
          isWithinInterval(new Date(p.date), {
            start: dateRange[0],
            end: dateRange[1],
          })
        )
        .reduce((sum, p) => {
          const t = p.type?.toLowerCase();
          const sign = isPositive(t) ? 1 : -1;
          return sum + sign * (Math.abs(p.amount) || 0);
        }, 0);
    }, [payments, dateRange]);

    // --- Visuals for Table ---
    const typeColor = (t) => {
      const type = t?.toLowerCase();
      if (type === "abort") return "default"; // grey
      if (isPositive(type)) return "success";
      return "error";
    };

  const [anchorEl, setAnchorEl] = useState(null);
  const openMenu = Boolean(anchorEl);
  const handleOpenMenu = (e) => setAnchorEl(e.currentTarget);
  const handleCloseMenu = () => setAnchorEl(null);
  const toggleColumn = (id) => {
    setVisibleColumns(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        // keep at least one column visible
        if (next.size > 1) next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };
  const onDragEnd = (result) => {
    if (!result.destination) return;
    const srcIdx = result.source.index;
    const dstIdx = result.destination.index;
    setColumnOrder(prev => {
      const next = [...prev];
      const [moved] = next.splice(srcIdx, 1);
      next.splice(dstIdx, 0, moved);
      return next;
    });
  };


    if (loading)
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
  if (error) return <Typography color="error">{error}</Typography>;

  const currencyColor = (cur) => {
    switch (cur) {
      case "USD": return "primary";
      case "EUR": return "secondary";
      case "GBP": return "info";
      default: return "default";
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box
        sx={{
          maxWidth: "1200px",
          margin: "40px auto",
          px: { xs: 2, md: 0 },
          fontFamily: `"Inter", "SF Pro Display", "Segoe UI", Roboto, Arial, sans-serif`,
        }}
      >
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

          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ width: { xs: "100%", md: "auto" } }}>
            <TextField
              label="Search payments"
              variant="outlined"
              size="medium"
              value={search}
              onChange={e => setSearch(e.target.value)}
              sx={{
                minWidth: { xs: "100%", sm: 260 },
                "& .MuiOutlinedInput-root": {
                  borderRadius: 2,
                  bgcolor: "background.paper",
                },
              }}
            />
            <DateRangePicker
              value={dateRange}
              onChange={setDateRange}
              localeText={{ start: "Start date", end: "End date" }}
              slotProps={{
                textField: {
                  size: "medium",
                  sx: {
                    "& .MuiOutlinedInput-root": { borderRadius: 2, bgcolor: "background.paper" },
                    minWidth: { xs: "100%", sm: 260 },
                  },
                },
              }}
            />
            <Button
              variant="outlined"
              onClick={handleOpenMenu}
              sx={{ whiteSpace: "nowrap" }}
            >
              Columns
            </Button>
            <Menu anchorEl={anchorEl} open={openMenu} onClose={handleCloseMenu}>
              {orderedColumns.map(col => (
                <MenuItem key={col.id} onClick={() => toggleColumn(col.id)}>
                  <Checkbox checked={visibleColumns.has(col.id)} />
                  <ListItemText primary={col.label} />
                </MenuItem>
              ))}
            </Menu>
          </Stack>
        </Box>

        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} md={4}>
            <Card
              elevation={0}
              sx={{
                borderRadius: 3,
                p: 0.5,
                background: "linear-gradient(135deg, #111827, #1f2937)",
                color: "white",
              }}
            >
              <CardContent sx={{ p: 2.5 }}>
                <Typography variant="overline" sx={{ opacity: 0.8 }}>
                  Total Sum
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 800 }}>
                  {totalSum.toFixed(2)}
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.8 }}>All time</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card
              elevation={0}
              sx={{
                borderRadius: 3,
                p: 0.5,
                background: "linear-gradient(135deg, #0f766e, #14b8a6)",
                color: "white",
              }}
            >
              <CardContent sx={{ p: 2.5 }}>
                <Typography variant="overline" sx={{ opacity: 0.9 }}>
                  This Month
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 800 }}>
                  {monthlySum.toFixed(2)}
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.9 }}>
                  {format(now, "MMMM yyyy")}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card
              elevation={0}
              sx={{
                borderRadius: 3,
                p: 0.5,
                background: "linear-gradient(135deg, #3730a3, #6366f1)",
                color: "white",
              }}
            >
              <CardContent sx={{ p: 2.5 }}>
                <Typography variant="overline" sx={{ opacity: 0.9 }}>
                  Custom Range
                </Typography>
                <Typography variant="h4" sx={{ fontWeight: 800 }}>
                  {customSum.toFixed(2)}
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.9 }}>
                  {dateRange[0] && dateRange[1]
                    ? `${format(dateRange[0], "MMM d")} – ${format(dateRange[1], "MMM d, yyyy")}`
                    : "Pick a date range"}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

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
              background:
                "linear-gradient(180deg, rgba(0,0,0,0.02), rgba(0,0,0,0))",
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
                      background:
                        "linear-gradient(90deg, rgba(99,102,241,0.06), rgba(99,102,241,0.00))",
                    },
                    "& .MuiTableCell-body": {
                      borderBottom: (t) => `1px dashed ${t.palette.divider}`,
                    },
                  }}
                >
                  {filteredPayments.map((p) => {
                    const t = p.type?.toLowerCase();
                    const isAbortType = isAbort(t);
                    const isPos = isPositive(t);
                    const isNeg = !isAbortType && !isPos;
                    return (
                      <TableRow key={p.id} hover>
                        {orderedColumns.map(col => {
                          if (!visibleColumns.has(col.id)) return null;
                          switch (col.id) {
                            case "date":
                              return (
                                <TableCell key={`${p.id}-date`} sx={{ whiteSpace: "nowrap" }}>
                                  <Stack direction="row" spacing={1} alignItems="center">
                                    <Avatar
                                      variant="rounded"
                                      sx={{
                                        width: 28,
                                        height: 28,
                                        bgcolor: "primary.main",
                                        color: "primary.contrastText",
                                        fontSize: 14,
                                        fontWeight: 700,
                                      }}
                                    >
                                      {format(new Date(p.date), "dd")}
                                    </Avatar>
                                    <Box>
                                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                                        {format(new Date(p.date), "MMM yyyy")}
                                      </Typography>
                                      <Typography variant="caption" color="text.secondary">
                                        {format(new Date(p.date), "EEE")}
                                      </Typography>
                                    </Box>
                                  </Stack>
                                </TableCell>
                              );
                            case "amount":
                              return (
                                <TableCell
                                  key={`${p.id}-amount`}
                                  align="right"
                                  sx={{
                                    fontWeight: 800,
                                    color: isAbortType
                                      ? "text.secondary"
                                      : isNeg
                                      ? "error.main"
                                      : "success.main",
                                  }}
                                >
                                  {isAbortType ? "—" : isPos ? "+" : "-"}
                                  {isAbortType ? "" : Math.abs(p.amount).toFixed(2)}
                                </TableCell>
                              );
                            case "currency":
                              return (
                                <TableCell key={`${p.id}-currency`}>
                                  <Chip
                                    size="small"
                                    label={p.currency}
                                    color={currencyColor(p.currency)}
                                    variant="outlined"
                                    sx={{ borderRadius: 1.5, fontWeight: 700 }}
                                  />
                                </TableCell>
                              );
                            case "merchant":
                              return (
                                <TableCell key={`${p.id}-merchant`} sx={{ maxWidth: 220 }}>
                                  <Tooltip title={p.merchant || ""}>
                                    <Typography noWrap>{p.merchant}</Typography>
                                  </Tooltip>
                                </TableCell>
                              );
                            case "auto_category":
                              return (
                                <TableCell key={`${p.id}-auto_category`} sx={{ maxWidth: 200 }}>
                                  <Chip
                                    size="small"
                                    label={p.auto_category || "—"}
                                    sx={{ borderRadius: 1.5, bgcolor: "action.selected" }}
                                  />
                                </TableCell>
                              );
                            case "source":
                              return (
                                <TableCell key={`${p.id}-source`}>
                                  <Typography variant="body2" color="text.secondary">
                                    {p.source}
                                  </Typography>
                                </TableCell>
                              );
                            case "type":
                              return (
                                <TableCell key={`${p.id}-type`}>
                                  <Chip
                                    size="small"
                                    label={p.type}
                                    color={typeColor(p.type)}
                                    sx={{
                                      borderRadius: 1.5,
                                      fontWeight: 700,
                                      bgcolor: t === "abort" ? "grey.300" : undefined,
                                      color: t === "abort" ? "text.secondary" : undefined,
                                    }}
                                  />
                                </TableCell>
                              );
                            case "note":
                              return (
                                <TableCell key={`${p.id}-note`} sx={{ maxWidth: 260 }}>
                                  <Tooltip title={p.note || ""}>
                                    <Typography noWrap color="text.secondary">
                                      {p.note || "—"}
                                    </Typography>
                                  </Tooltip>
                                </TableCell>
                              );
                            case "cust_category":
                              return (
                                <TableCell key={`${p.id}-cust_category`} sx={{ maxWidth: 200 }}>
                                  <Chip
                                    size="small"
                                    label={p.cust_category || "—"}
                                    variant="outlined"
                                    sx={{ borderRadius: 1.5 }}
                                  />
                                </TableCell>
                              );
                            default:
                              return null;
                          }
                        })}
                      </TableRow>
                    );
                  })}
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