import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Stack,
  Box,
  Typography,
  Divider,
  Button,
  IconButton,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import TableControls from "./TableControls";

export default function SettingsDialog({
  open,
  onClose,
  setManagerOpen,
  dateRange,
  setDateRange,
  orderedColumns,
  visibleColumns,
  toggleColumn,
}) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        className: "settings-dialog-paper"
      }}
    >
      <DialogTitle className="settings-dialog-title">
        <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: -0.01 }}>
          Settings
        </Typography>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent sx={{ pt: 3 }}>
        <Stack spacing={3}>
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
              Date Range
            </Typography>
            <TableControls
              search=""
              setSearch={() => {}}
              dateRange={dateRange}
              setDateRange={setDateRange}
              orderedColumns={orderedColumns}
              visibleColumns={visibleColumns}
              toggleColumn={toggleColumn}
              showSearch={false}
            />
          </Box>
          <Divider />
          <Box>
            <Button
              variant="contained"
              fullWidth
              onClick={() => {
                onClose();
                setManagerOpen(true);
              }}
              className="settings-dialog-manage-btn"
            >
              Manage Categories
            </Button>
          </Box>
        </Stack>
      </DialogContent>
    </Dialog>
  );
}

