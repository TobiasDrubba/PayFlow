import React, { useEffect, useState, useMemo } from "react";
import { fetchPayments } from "./api";
import {
  Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Paper, CircularProgress, Typography, TextField,
  Box, Grid, Card, CardContent
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
    () => payments.reduce((sum, p) => sum + (p.amount || 0), 0),
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
        .reduce((sum, p) => sum + (p.amount || 0), 0),
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
      .reduce((sum, p) => sum + (p.amount || 0), 0);
  }, [payments, dateRange]);

  if (loading) return <CircularProgress />;
  if (error) return <Typography color="error">{error}</Typography>;

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box sx={{ maxWidth: "90%", margin: "auto", mt: 4 }}>
        <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
          <Grid item xs={12} md={4}>
            <TextField
              label="Search"
              variant="outlined"
              fullWidth
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </Grid>
          <Grid item xs={12} md={8}>
            <DateRangePicker
              startText="Start date"
              endText="End date"
              value={dateRange}
              onChange={setDateRange}
              renderInput={(startProps, endProps) => (
                <React.Fragment>
                  <TextField {...startProps} sx={{ mr: 2 }} />
                  <TextField {...endProps} />
                </React.Fragment>
              )}
            />
          </Grid>
        </Grid>
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">Total Sum</Typography>
                <Typography variant="h6">{totalSum.toFixed(2)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">This Month</Typography>
                <Typography variant="h6">{monthlySum.toFixed(2)}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">Custom Range</Typography>
                <Typography variant="h6">{customSum.toFixed(2)}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
        <TableContainer component={Paper} sx={{ borderRadius: 3, boxShadow: 3 }}>
          <Table>
            <TableHead sx={{ backgroundColor: "#f5f5f5" }}>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>Amount</TableCell>
                <TableCell>Currency</TableCell>
                <TableCell>Merchant</TableCell>
                <TableCell>Auto Category</TableCell>
                <TableCell>Source</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Note</TableCell>
                <TableCell>Custom Category</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredPayments.map((p) => (
                <TableRow key={p.id} hover>
                  <TableCell>{format(new Date(p.date), "yyyy-MM-dd")}</TableCell>
                  <TableCell>{p.amount.toFixed(2)}</TableCell>
                  <TableCell>{p.currency}</TableCell>
                  <TableCell>{p.merchant}</TableCell>
                  <TableCell>{p.auto_category}</TableCell>
                  <TableCell>{p.source}</TableCell>
                  <TableCell>{p.type}</TableCell>
                  <TableCell>{p.note}</TableCell>
                  <TableCell>{p.cust_category}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </LocalizationProvider>
  );
}
