import React, { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  Stack,
  InputAdornment,
  IconButton,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { DateTimePicker, LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import { submitCustomPayment } from "../api";
import Autocomplete from "@mui/material/Autocomplete";

// Enum values must match backend
const PAYMENT_TYPES = [
  { value: "income", label: "Income" },
  { value: "expense", label: "Expense" },
  { value: "abort", label: "Abort" },
  { value: "refund", label: "Refund" },
];

const PAYMENT_SOURCES = [
  { value: "Alipay", label: "Alipay" },
  { value: "WeChat", label: "WeChat" },
  { value: "Tsinghua Card", label: "Tsinghua Card" },
  { value: "Other", label: "Other" },
];

export default function AddCustomPaymentDialog({ open, onClose, categories = [], onSubmitted }) {
  const [form, setForm] = useState({
    date: new Date(),
    amount: "",
    currency: "CNY",
    merchant: "",
    type: "expense",
    source: "",
    note: "",
    category: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Clear error when dialog is closed
  React.useEffect(() => {
    if (!open) setError("");
  }, [open]);

  const handleChange = (field) => (e) => {
    setForm((prev) => ({
      ...prev,
      [field]: e.target.value,
    }));
  };

  const handleDateChange = (date) => {
    setForm((prev) => ({
      ...prev,
      date,
    }));
  };

  const handleCategoryChange = (_, value) => {
    setForm((prev) => ({
      ...prev,
      category: value || "",
    }));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError("");
    try {
      const payload = {
        ...form,
        amount: parseFloat(form.amount),
        date: form.date instanceof Date ? form.date.toISOString() : form.date,
        source: form.source || undefined,
        note: form.note || undefined,
        category: form.category || undefined,
      };
      await submitCustomPayment(payload);
      setSubmitting(false);
      if (onSubmitted) onSubmitted(); // refetch payments table
      onClose();
    } catch (e) {
      setError(e.message || "Failed to submit payment.");
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        className: "settings-dialog-paper",
        sx: {
          borderRadius: "20px",
          boxShadow: "0 12px 48px rgba(0,0,0,0.12)",
        }
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontWeight: 700,
          letterSpacing: -0.01,
        }}
      >
        <span>Add Custom Payment</span>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent sx={{ pt: 3 }}>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <DateTimePicker
              label="Date & Time"
              value={form.date}
              onChange={handleDateChange}
              renderInput={(params) => <TextField {...params} fullWidth />}
              maxDateTime={new Date()}
            />
          </LocalizationProvider>
          <TextField
            label="Amount"
            type="number"
            value={form.amount}
            onChange={handleChange("amount")}
            fullWidth
            InputProps={{
              startAdornment: <InputAdornment position="start">{form.currency}</InputAdornment>,
              inputProps: { min: 0, step: "0.01" },
            }}
            required
          />
          <TextField
            label="Currency"
            value={form.currency}
            onChange={handleChange("currency")}
            fullWidth
            required
          />
          <TextField
            label="Merchant"
            value={form.merchant}
            onChange={handleChange("merchant")}
            fullWidth
            required
          />
          <TextField
            select
            label="Type"
            value={form.type}
            onChange={handleChange("type")}
            fullWidth
            required
          >
            {PAYMENT_TYPES.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Source"
            value={form.source}
            onChange={handleChange("source")}
            fullWidth
            helperText="Optional. Defaults to 'Other'."
          >
            <MenuItem value="">(Not specified)</MenuItem>
            {PAYMENT_SOURCES.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Note"
            value={form.note}
            onChange={handleChange("note")}
            fullWidth
            multiline
            minRows={1}
            maxRows={3}
          />
          <Autocomplete
            size="small"
            value={form.category || null}
            options={categories}
            freeSolo={false}
            onChange={handleCategoryChange}
            renderInput={params => (
              <TextField
                {...params}
                label="Category"
                variant="outlined"
                placeholder="Select category"
                helperText="Optional custom category"
                fullWidth
              />
            )}
            sx={{ minWidth: 180 }}
            clearOnEscape
          />
          {error && (
            <Typography color="error" fontSize={13} mt={0.5}>
              {error}
            </Typography>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button
          onClick={handleSubmit}
          variant="contained"
          className="settings-dialog-manage-btn"
          disabled={submitting || !form.amount || !form.merchant || !form.type || !form.currency}
        >
          {submitting ? "Submitting..." : "Submit"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
