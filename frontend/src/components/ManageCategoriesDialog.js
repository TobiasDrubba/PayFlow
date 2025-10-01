import React, { useEffect, useState } from "react";
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Box, TextField, DialogContentText } from "@mui/material";

// Helper to get all child categories (leaf nodes with value null)
function getAllChildCategories(tree) {
  const result = [];
  function traverse(node) {
    if (!node || typeof node !== "object") return;
    for (const [key, value] of Object.entries(node)) {
      if (value === null) {
        result.push(key);
      } else if (typeof value === "object") {
        traverse(value);
      }
    }
  }
  traverse(tree);
  return result;
}

export default function ManageCategoriesDialog({
  open,
  onClose,
  categoryTree,
  onUpdate,
  payments = []
}) {
  const [rawJson, setRawJson] = useState(JSON.stringify(categoryTree, null, 2));
  const [parsed, setParsed] = useState(categoryTree);
  const [parseError, setParseError] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deletedCategories, setDeletedCategories] = useState([]);
  const [affectedPayments, setAffectedPayments] = useState([]);

  useEffect(() => {
    setParsed(categoryTree);
    try {
      setRawJson(JSON.stringify(categoryTree, null, 2));
      setParseError(null);
    } catch (e) {
      setRawJson("");
      setParseError("Invalid initial JSON");
    }
  }, [categoryTree]);

  const handleSave = () => {
    if (parseError) return;
    // Check for deleted child categories
    const oldChildCats = getAllChildCategories(categoryTree);
    const newChildCats = getAllChildCategories(parsed);
    const deleted = oldChildCats.filter(cat => !newChildCats.includes(cat));
    if (deleted.length > 0 && payments.length > 0) {
      const affected = payments.filter(p => deleted.includes(p.cust_category));
      if (affected.length > 0) {
        setDeletedCategories(deleted);
        setAffectedPayments(affected);
        setConfirmOpen(true);
        return;
      }
    }
    onUpdate(parsed);
    onClose();
  };

  const handleConfirm = () => {
    setConfirmOpen(false);
    onUpdate(parsed);
    onClose();
  };

  // Reset the edited tree to the original
  const resetToOriginal = () => {
    setParsed(categoryTree);
    setRawJson(JSON.stringify(categoryTree, null, 2));
    setParseError(null);
  };

  const handleCancelConfirm = () => {
    setConfirmOpen(false);
    resetToOriginal();
  };

  const handleMainCancel = () => {
    resetToOriginal();
    onClose();
  };

  return (
    <>
      <Dialog open={open} onClose={handleMainCancel} maxWidth="md" fullWidth>
        <DialogTitle>Manage Categories</DialogTitle>
        <DialogContent>
          <Box sx={{ height: 500 }}>
            <TextField
              label="Categories JSON"
              value={rawJson}
              onChange={(e) => {
                const v = e.target.value;
                setRawJson(v);
                try {
                  const obj = JSON.parse(v);
                  setParsed(obj);
                  setParseError(null);
                } catch (err) {
                  setParseError(err.message);
                }
              }}
              multiline
              minRows={14}
              maxRows={24}
              fullWidth
              error={!!parseError}
              helperText={parseError ? `Invalid JSON: ${parseError}` : "Edit the JSON and click Save Changes"}
              FormHelperTextProps={{ sx: { fontFamily: "monospace" } }}
              InputProps={{
                sx: { fontFamily: "monospace", whiteSpace: "pre", alignItems: "start" }
              }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleMainCancel}>Cancel</Button>
          <Button variant="contained" color="primary" onClick={handleSave} disabled={!!parseError}>
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog open={confirmOpen} onClose={handleCancelConfirm}>
        <DialogTitle>Confirm Category Deletion</DialogTitle>
        <DialogContent>
          <DialogContentText>
            The following categories will be removed from the tree:
            <ul>
              {deletedCategories.map(cat => (
                <li key={cat}><b>{cat}</b></li>
              ))}
            </ul>
            {affectedPayments.length > 0 && (
              <>
                <b>{affectedPayments.length}</b> payment(s) currently use these categories and will become uncategorized.<br />
                Are you sure you want to proceed?
              </>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelConfirm}>Cancel</Button>
          <Button variant="contained" color="error" onClick={handleConfirm}>
            Yes, update and uncategorize payments
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}