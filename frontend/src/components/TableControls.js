import React, { useState } from "react";
import {
  Stack,
  TextField,
  Button,
  Menu,
  MenuItem,
  Checkbox,
  ListItemText
} from "@mui/material";
import { DateRangePicker } from "@mui/x-date-pickers-pro/DateRangePicker";

export default function TableControls({
  search,
  setSearch,
  dateRange,
  setDateRange,
  orderedColumns,
  visibleColumns,
  toggleColumn
}) {
  const [anchorEl, setAnchorEl] = useState(null);
  const openMenu = Boolean(anchorEl);

  const handleOpenMenu = (e) => setAnchorEl(e.currentTarget);
  const handleCloseMenu = () => setAnchorEl(null);

  return (
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
  );
}