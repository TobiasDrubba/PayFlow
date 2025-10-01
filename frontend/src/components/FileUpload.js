import React, { useState } from "react";
import { Box, Stack, Button, Typography } from "@mui/material";
import { uploadPaymentFiles } from "../api";

const paymentSourceOptions = [
  { value: "Alipay", label: "Alipay" },
  { value: "WeChat", label: "WeChat" },
  { value: "Tsinghua Card", label: "Tsinghua Card" },
];

export default function FileUpload({ onSuccess }) {
  const [uploadFiles, setUploadFiles] = useState([]); // [{file, type}]
  const [uploadError, setUploadError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [successFiles, setSuccessFiles] = useState([]); // [{name, type}]

  const handleFileChange = (e) => {
    setUploadError("");
    setSuccessFiles([]);
    const files = Array.from(e.target.files).slice(0, 3);
    setUploadFiles(files.map(file => ({ file, type: "" })));
  };

  const handleTypeChange = (idx, type) => {
    setUploadFiles(files =>
      files.map((f, i) => (i === idx ? { ...f, type } : f))
    );
  };

  const handleUpload = async () => {
    setUploadError("");
    setSuccessFiles([]);
    if (!uploadFiles.length) {
      setUploadError("Please select up to 3 files.");
      return;
    }
    if (uploadFiles.some(f => !f.type)) {
      setUploadError("Please select a type for each file.");
      return;
    }
    setUploading(true);
    try {
      await uploadPaymentFiles(uploadFiles);
      setSuccessFiles(uploadFiles.map(f => ({ name: f.file.name, type: f.type })));
      setUploadFiles([]);
      setUploadError("");
      if (onSuccess) onSuccess();
    } catch (err) {
      setUploadError(err.message || "Upload failed");
    }
    setUploading(false);
  };

  return (
    <Box sx={{ mb: 2 }}>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center">
        <input
          type="file"
          multiple
          accept=".csv,.xls,.xlsx"
          style={{ display: "none" }}
          id="file-upload"
          onChange={handleFileChange}
          disabled={uploading}
        />
        <label htmlFor="file-upload">
          <Button variant="outlined" component="span" disabled={uploading}>
            Select Files (max 3)
          </Button>
        </label>
        {uploadFiles.map((f, idx) => (
          <Stack key={f.file.name} direction="row" spacing={1} alignItems="center">
            <Typography>{f.file.name}</Typography>
            <select
              value={f.type}
              onChange={e => handleTypeChange(idx, e.target.value)}
              disabled={uploading}
              style={{ height: 32 }}
            >
              <option value="">Select Type</option>
              {paymentSourceOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </Stack>
        ))}
        <Button
          variant="contained"
          color="primary"
          onClick={handleUpload}
          disabled={uploading || !uploadFiles.length || uploadFiles.some(f => !f.type)}
        >
          {uploading ? "Uploading..." : "Upload"}
        </Button>
        {uploadError && (
          <Typography color="error" sx={{ ml: 2 }}>
            {uploadError}
          </Typography>
        )}
      </Stack>
      {successFiles.length > 0 && (
        <Box sx={{ mt: 1 }}>
          {successFiles.map(f => (
            <Typography key={f.name} color="success.main">
              Imported: {f.name} ({f.type})
            </Typography>
          ))}
        </Box>
      )}
    </Box>
  );
}

