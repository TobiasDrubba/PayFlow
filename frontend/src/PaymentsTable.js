import React, { useEffect, useState } from "react";
import { fetchPayments } from "./api";
import {
  Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Paper, CircularProgress, Typography
} from "@mui/material";

export default function PaymentsTable() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPayments()
      .then(data => setPayments(data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <CircularProgress />;
  if (error) return <Typography color="error">{error}</Typography>;

  return (
    <TableContainer component={Paper} sx={{ maxWidth: "90%", margin: "auto", mt: 4 }}>
      <Table>
        <TableHead>
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
          {payments.map((p) => (
            <TableRow key={p.id}>
              <TableCell>{new Date(p.date).toLocaleDateString()}</TableCell>
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
  );
}
