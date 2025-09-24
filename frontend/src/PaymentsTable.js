import React, { useEffect, useState, useMemo } from "react";
import { fetchPayments } from "./api";
import {
  Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Paper, CircularProgress, Typography, TextField,
  Box, Grid, Card, CardContent, Chip, Avatar, Stack, Tooltip, Divider
} from "@mui/material";
import { DateRangePicker } from "@mui/x-date-pickers-pro/DateRangePicker";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { format, isWithinInterval, startOfMonth, endOfMonth } from "date-fns";
export default function PaymentsTable() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [dateRange, setDateRange] = useState([null, null]);

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

  // Calculate sums
  const totalSum = useMemo(
    () =>
      payments.reduce((sum, p) => {
        const t = p.type?.toLowerCase();
        const sign = (t === "income" || t === "none") || !t ? 1 : -1;
        return sum + sign * (Math.abs(p.amount) || 0);
      }, 0),
    [payments]
  );

  const now = new Date();
  const monthlySum = useMemo(
() =>
      payments
        .filter(p =>
          isWithinInterval(new Date(p.date), {
            start: startOfMonth(now),
            end: endOfMonth(now),
          })
        )
        .reduce((sum, p) => {
          const t = p.type?.toLowerCase();
          const sign = (t === "income" || t === "none") || !t ? 1 : -1;
          return sum + sign * (Math.abs(p.amount) || 0);
        }, 0),
    [payments, now]
  );

  const customSum = useMemo(() => {
    if (!dateRange[0] || !dateRange[1]) return 0;
    return payments
      .filter(p =>
        isWithinInterval(new Date(p.date), {
          start: dateRange[0],
          end: dateRange[1],
        })
      )
      .reduce((sum, p) => {
        const t = p.type?.toLowerCase();
        const sign = (t === "income" || t === "none") || !t ? 1 : -1;
        return sum + sign * (Math.abs(p.amount) || 0);
      }, 0);
  }, [payments, dateRange]);

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

  const typeColor = (t) => (t?.toLowerCase() === "debit" ? "error" : "success");

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
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell>Currency</TableCell>
                  <TableCell>Merchant</TableCell>
                  <TableCell>Auto Category</TableCell>
                  <TableCell>Source</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Note</TableCell>
                  <TableCell>Custom Category</TableCell>
                </TableRow>
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
                  const isNegative = !((t === "income" || t === "none") || !t);
                  return (
                    <TableRow key={p.id} hover>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>
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
                      <TableCell
                        align="right"
                        sx={{ fontWeight: 800, color: isNegative ? "error.main" : "success.main" }}
                      >
                        {((t === "income" || t === "none") || !t) ? "+" : "-"}
                         {Math.abs(p.amount).toFixed(2)}
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={p.currency}
                          color={currencyColor(p.currency)}
                          variant="outlined"
                          sx={{ borderRadius: 1.5, fontWeight: 700 }}
                        />
                      </TableCell>
                      <TableCell sx={{ maxWidth: 220 }}>
                        <Tooltip title={p.merchant || ""}>
                          <Typography noWrap>{p.merchant}</Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell sx={{ maxWidth: 200 }}>
                        <Chip
                          size="small"
                          label={p.auto_category || "—"}
                          sx={{ borderRadius: 1.5, bgcolor: "action.selected" }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {p.source}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={p.type}
                          color={typeColor(p.type)}
                          sx={{ borderRadius: 1.5, fontWeight: 700 }}
                        />
                      </TableCell>
                      <TableCell sx={{ maxWidth: 260 }}>
                        <Tooltip title={p.note || ""}>
                          <Typography noWrap color="text.secondary">
                            {p.note || "—"}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell sx={{ maxWidth: 200 }}>
                        <Chip
                          size="small"
                          label={p.cust_category || "—"}
                          variant="outlined"
                          sx={{ borderRadius: 1.5 }}
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
                {filteredPayments.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={9} align="center" sx={{ py: 6, color: "text.secondary" }}>
                      No results. Try adjusting filters.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      </Box>
    </LocalizationProvider>
  );
}