import React, { useEffect, useState } from "react";
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Box, TextField } from "@mui/material";

export default function ManageCategoriesDialog({
  open,
  onClose,
  categoryTree,
  onUpdate
}) {
  const [rawJson, setRawJson] = useState(JSON.stringify(categoryTree, null, 2));
  const [parsed, setParsed] = useState(categoryTree);
  const [parseError, setParseError] = useState(null);

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
    onUpdate(parsed);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
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
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" color="primary" onClick={handleSave} disabled={!!parseError}>
          Save Changes
        </Button>
      </DialogActions>
    </Dialog>
  );
}