import React, { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Stack,
  Box,
  Divider,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Checkbox,
  ListItemText
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { DateRangePicker } from "@mui/x-date-pickers-pro/DateRangePicker";
import { downloadAllPayments } from "../api";

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
  const [anchorEl, setAnchorEl] = useState(null);
  const openMenu = Boolean(anchorEl);

  const handleOpenMenu = (e) => setAnchorEl(e.currentTarget);
  const handleCloseMenu = () => setAnchorEl(null);

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
        <span style={{ fontWeight: 700, letterSpacing: -0.01 }}>Settings</span>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent sx={{ pt: 3 }}>
        <Stack spacing={3}>
          <Box>
            <DateRangePicker
              value={dateRange}
              onChange={setDateRange}
              localeText={{ start: "Start date", end: "End date" }}
              slotProps={{
                textField: {
                  fullWidth: true,
                  variant: "outlined",
                  sx: {
                    width: "100%",
                    borderRadius: "12px",
                    bgcolor: "background.paper",
                    "& .MuiInputBase-root": {
                      borderRadius: "12px",
                      fontWeight: 600,
                      fontSize: "1rem",
                      background: "white",
                      border: "2px solid #667eea",
                      boxShadow: "0 4px 12px rgba(102, 126, 234, 0.10)",
                      transition: "all 250ms cubic-bezier(0.4, 0, 0.2, 1)",
                    },
                    "& .MuiOutlinedInput-notchedOutline": {
                      border: "none"
                    },
                    marginTop: "16px"
                  },
                  InputProps: {
                    sx: {
                      borderRadius: "12px",
                      fontWeight: 600,
                      fontSize: "1rem",
                      background: "white",
                    },
                  },
                  label: "Set Custom Sum Date Range",
                  placeholder: "Set Custom Sum Date Range",
                },
              }}
            />
          </Box>
          <Divider />
          <Box>
            <Button
              variant="contained"
              fullWidth
              onClick={handleOpenMenu}
              className="settings-dialog-manage-btn"
              id="columns-menu-btn"
              sx={{ width: "100%" }}
            >
              Enable/Disable Columns
            </Button>
            <Menu
              anchorEl={anchorEl}
              open={openMenu}
              onClose={handleCloseMenu}
              MenuListProps={{
                sx: {
                  width: anchorEl ? anchorEl.offsetWidth : undefined,
                  minWidth: anchorEl ? anchorEl.offsetWidth : undefined,
                  maxWidth: anchorEl ? anchorEl.offsetWidth : undefined,
                }
              }}
              PaperProps={{
                sx: {
                  width: anchorEl ? anchorEl.offsetWidth : undefined,
                  minWidth: anchorEl ? anchorEl.offsetWidth : undefined,
                  maxWidth: anchorEl ? anchorEl.offsetWidth : undefined,
                }
              }}
            >
              {orderedColumns.map(col => (
                <MenuItem key={col.id} onClick={() => toggleColumn(col.id)}>
                  <Checkbox checked={visibleColumns.has(col.id)} />
                  <ListItemText primary={col.label} />
                </MenuItem>
              ))}
            </Menu>
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
          {/* Download All Payments Button */}
          <Divider />
          <Box>
            <Button
              variant="contained"
              fullWidth
              onClick={async () => {
                try {
                  await downloadAllPayments();
                } catch (e) {
                  alert("Failed to download payments.");
                }
              }}
              className="settings-dialog-manage-btn"
              sx={{ mt: 1 }}
            >
              Download All Payments
            </Button>
          </Box>
        </Stack>
      </DialogContent>
    </Dialog>
  );
}
