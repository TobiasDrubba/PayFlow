import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  IconButton
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title = "Confirm Delete",
  description = "Are you sure you want to delete this? This action cannot be undone.",
  confirmText = "Delete",
  cancelText = "Cancel",
  loading = false,
}) {
  // Determine button class based on confirmText
  let confirmClass = "btn-save";
  if (confirmText.toLowerCase().includes("delete")) confirmClass = "btn-delete";
  if (confirmText.toLowerCase().includes("save")) confirmClass = "btn-save";
  if (confirmText.toLowerCase().includes("cancel")) confirmClass = "btn-cancel";

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: "16px",
          boxShadow: "0 4px 24px rgba(102, 126, 234, 0.15)",
        }
      }}
    >
      <DialogTitle sx={{ fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        {title}
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Typography variant="body1" sx={{ mb: 2 }}>
          {description}
        </Typography>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} variant="outlined" color="primary" disabled={loading} className="btn-cancel">
          {cancelText}
        </Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          color={confirmClass === "btn-delete" ? "error" : "success"}
          disabled={loading}
          className={confirmClass}
        >
          {confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
