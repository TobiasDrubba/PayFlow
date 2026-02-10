import React from "react";
import {
  TableRow,
  TableCell,
  Stack,
  Avatar,
  Box,
  Typography,
  Chip,
  Tooltip,
  TextField,
  Autocomplete
} from "@mui/material";
import { format } from "date-fns";

export default function PaymentTableRow({
  payment,
  orderedColumns,
  visibleColumns,
  categories,
  onCategoryChange,
  selected = false,
  onRowClick,
  onRowContextMenu,
}) {
  const isPositive = (t) => t === "income" || t === "refund";
  const isAbort = (t) => t === "abort";

  const typeColor = (t) => {
    const type = t?.toLowerCase();
    if (type === "abort") return "default";
    if (isPositive(type)) return "success";
    return "error";
  };

  const currencyColor = (cur) => {
    switch (cur) {
      case "USD": return "primary";
      case "EUR": return "secondary";
      case "GBP": return "info";
      default: return "default";
    }
  };

  const t = payment.type?.toLowerCase();
  const isAbortType = isAbort(t);
  const isPos = isPositive(t);
  const isNeg = !isAbortType && !isPos;

  // Get currency from localStorage, default to CNY
  const displayCurrency = (typeof window !== "undefined" && localStorage.getItem("currency")) || "CNY";

  const renderCell = (col) => {
    switch (col.id) {
      case "date":
        return (
          <TableCell key={`${payment.id}-date`} sx={{ whiteSpace: "nowrap" }}>
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
                {format(new Date(payment.date), "dd")}
              </Avatar>
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                  {format(new Date(payment.date), "MMM yyyy")}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {format(new Date(payment.date), "EEE")}, {format(new Date(payment.date), "HH:mm")}
                </Typography>
              </Box>
            </Stack>
          </TableCell>
        );

      case "amount":
        // Show symbol according to selected currency
        let symbol = "元";
        if (displayCurrency === "USD") symbol = "$";
        else if (displayCurrency === "EUR") symbol = "€";
        if (displayCurrency !== "CNY") symbol = displayCurrency;
        return (
          <TableCell
            key={`${payment.id}-amount`}
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
            {isAbortType ? "" : `${Math.abs(payment.amount).toFixed(2)} ${symbol}`}
          </TableCell>
        );

      case "currency":
        // Always show the selected currency, not the original payment currency
        return (
          <TableCell key={`${payment.id}-currency`}>
            <Chip
              size="small"
              label={displayCurrency}
              color={currencyColor(displayCurrency)}
              variant="outlined"
              sx={{ borderRadius: 1.5, fontWeight: 700 }}
            />
          </TableCell>
        );

      case "merchant":
        return (
          <TableCell key={`${payment.id}-merchant`} sx={{ maxWidth: 220 }}>
            <Tooltip title={payment.merchant || ""}>
              <Typography noWrap>{payment.merchant}</Typography>
            </Tooltip>
          </TableCell>
        );

      case "auto_category":
        return (
          <TableCell key={`${payment.id}-auto_category`} sx={{ maxWidth: 200 }}>
            <Chip
              size="small"
              label={payment.auto_category || "—"}
              sx={{ borderRadius: 1.5, bgcolor: "action.selected" }}
            />
          </TableCell>
        );

      case "source":
        return (
          <TableCell key={`${payment.id}-source`}>
            <Typography variant="body2" color="text.secondary">
              {payment.source}
            </Typography>
          </TableCell>
        );

      case "type":
        return (
          <TableCell key={`${payment.id}-type`}>
            <Chip
              size="small"
              label={payment.type}
              color={typeColor(payment.type)}
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
          <TableCell key={`${payment.id}-note`} sx={{ maxWidth: 260 }}>
            <Tooltip title={payment.note || ""}>
              <Typography noWrap color="text.secondary">
                {payment.note || "—"}
              </Typography>
            </Tooltip>
          </TableCell>
        );

      case "cust_category":
        return (
          <TableCell key={`${payment.id}-cust_category`} sx={{ maxWidth: 400 }}>
            <Autocomplete
              size="small"
              value={payment.cust_category || null}
              options={categories}
              freeSolo={false}
              onChange={(_, value) => onCategoryChange(payment, value || "")}
              renderInput={params => (
                <TextField
                  {...params}
                  variant="standard"
                  placeholder="—"
                  InputProps={{
                    ...params.InputProps,
                    // Show clear button
                    endAdornment: params.InputProps.endAdornment,
                  }}
                />
              )}
              sx={{ minWidth: 180 }}
              clearOnEscape
            />
          </TableCell>
        );

      default:
        return null;
    }
  };

  return (
    <TableRow
      key={payment.id}
      hover
      selected={selected}
      sx={selected ? { backgroundColor: "rgba(102,126,234,0.08) !important" } : {}}
      onClick={onRowClick ? (e) => onRowClick(payment, e) : undefined}
      onContextMenu={onRowContextMenu ? (e) => onRowContextMenu(payment, e) : undefined}
      style={{ cursor: "pointer" }}
    >
      {orderedColumns.map(col => {
        if (!visibleColumns.has(col.id)) return null;
        return renderCell(col);
      })}
    </TableRow>
  );
}