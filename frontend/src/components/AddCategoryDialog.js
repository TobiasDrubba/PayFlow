import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";

export default function AddCategoryDialog({
  open,
  onClose,
  newCat,
  setNewCat,
  onAdd
}) {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Add New Category</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          margin="dense"
          label="Category Name"
          fullWidth
          value={newCat}
          onChange={e => setNewCat(e.target.value)}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={onAdd}
          disabled={!newCat.trim()}
          variant="contained"
          startIcon={<AddIcon />}
        >
          Add
        </Button>
      </DialogActions>
    </Dialog>
  );
}