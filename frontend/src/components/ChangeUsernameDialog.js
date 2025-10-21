import React, { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  IconButton,
  TextField,
  Typography
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { changeUsername } from "../api";

export default function ChangeUsernameDialog({ open, onClose, onChanged }) {
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = async () => {
    setLoading(true);
    setError("");
    try {
      await changeUsername(username);
      onChanged && onChanged(username);
      onClose();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>
        Change Username
        <IconButton onClick={onClose} size="small" sx={{ position: "absolute", right: 8, top: 8 }}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <TextField
          label="New Username"
          value={username}
          onChange={e => setUsername(e.target.value)}
          fullWidth
          autoFocus
          margin="normal"
        />
        {error && <Typography color="error">{error}</Typography>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading} className="btn-cancel">Cancel</Button>
        <Button
          onClick={handleChange}
          disabled={loading || !username}
          variant="contained"
          className="btn-save"
        >
          Change Username
        </Button>
      </DialogActions>
    </Dialog>
  );
}
