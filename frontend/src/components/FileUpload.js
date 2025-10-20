import React, { useState } from "react";
import { uploadPaymentFiles } from "../api";
import "./FileUpload.css";

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

  const inferFileType = (fileName) => {
    const lowerName = fileName.toLowerCase();
    if (lowerName.includes("支付宝") || lowerName.includes("alipay")) {
      return "Alipay";
    }
    if (lowerName.includes("微信") || lowerName.includes("wechat")) {
      return "WeChat";
    }
    if (lowerName.includes("tsinghua") || lowerName.includes("card")) {
      return "Tsinghua Card";
    }
    return ""; // Default to empty if no match
  };

  const handleFileChange = (e) => {
    setUploadError("");
    setSuccessFiles([]);
    const files = Array.from(e.target.files).slice(0, 3);
    setUploadFiles(
      files.map((file) => ({
        file,
        type: inferFileType(file.name), // Infer type from file name
      }))
    );
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

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getFileIcon = (fileName) => {
    const ext = fileName.split('.').pop().toLowerCase();
    if (ext === 'csv') return '📊';
    if (ext === 'xlsx' || ext === 'xls') return '📈';
    return '📄';
  };

  return (
    <div className={`upload-container ${uploadFiles.length > 0 ? 'has-files' : ''}`}>
      {uploading && (
        <div className="uploading-overlay">
          <div className="uploading-content">
            <div className="uploading-spinner"></div>
            <div className="uploading-text">Uploading your files...</div>
          </div>
        </div>
      )}

      <div className="upload-header">
        <div className="upload-icon">📤</div>
        <div className="upload-header-text">
          <h3>Upload Payment Files</h3>
          <p>Select up to 3 CSV or Excel files to import transactions</p>
        </div>
      </div>

      <div className="upload-actions">
        <input
          type="file"
          multiple
          accept=".csv,.xls,.xlsx"
          style={{ display: "none" }}
          id="file-upload-input"
          onChange={handleFileChange}
          disabled={uploading}
        />
        <label htmlFor="file-upload-input">
          <button
            className="upload-btn select-files-btn"
            disabled={uploading}
            onClick={(e) => {
              e.preventDefault();
              document.getElementById('file-upload-input').click();
            }}
            type="button"
          >
            <span className="upload-btn-icon">📁</span>
            <span>Select Files</span>
          </button>
        </label>

        {uploadFiles.length > 0 && (
          <button
            className="upload-btn"
            onClick={handleUpload}
            disabled={uploading || !uploadFiles.length || uploadFiles.some(f => !f.type)}
            type="button"
          >
            <span className="upload-btn-icon">⬆️</span>
            <span>{uploading ? "Uploading..." : `Upload ${uploadFiles.length} ${uploadFiles.length === 1 ? 'File' : 'Files'}`}</span>
          </button>
        )}
      </div>

      {uploadFiles.length > 0 && (
        <div className="file-list">
          {uploadFiles.map((f, idx) => (
            <div key={f.file.name} className="file-item" style={{ position: "relative", zIndex: 1 }}>
              <div className="file-icon">{getFileIcon(f.file.name)}</div>
              <div className="file-info" style={{ minWidth: 0 }}>
                <p className="file-name">{f.file.name}</p>
                <p className="file-size">{formatFileSize(f.file.size)}</p>
              </div>
              {/* Ensure the select is not overlapped by anything */}
              <select
                className={`file-type-select ${!f.type ? 'empty' : ''}`}
                value={f.type}
                onChange={e => handleTypeChange(idx, e.target.value)}
                disabled={uploading}
              >
                <option value="">Select Type</option>
                {paymentSourceOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}

      {uploadError && (
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          <span>{uploadError}</span>
        </div>
      )}

      {successFiles.length > 0 && (
        <div className="success-list">
          {successFiles.map(f => (
            <div key={f.name} className="success-item">
              <span className="success-icon">✓</span>
              <span>Successfully imported: {f.name} ({f.type})</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}