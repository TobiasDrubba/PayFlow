import React, { useState, useEffect, useRef } from "react";
import {
  uploadPaymentFiles,
  fetchCurrentUser,
  fetchMailgunCache,
  importMailgunCached,
  removeMailgunCacheFile, // <-- existing import
} from "../api";
import ConfirmDialog from "./ConfirmDialog"; // <-- new import
import "./FileUpload.css";

const paymentSourceOptions = [
  { value: "Alipay", label: "Alipay" },
  { value: "WeChat", label: "WeChat" },
  { value: "Tsinghua Card", label: "Tsinghua Card" },
  { value: "Other", label: "Other" },
];

export default function FileUpload({ onSuccess, dialogOpen }) {
  const [uploadFiles, setUploadFiles] = useState([]); // [{file, type}]
  const [uploadError, setUploadError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [successFiles, setSuccessFiles] = useState([]); // [{name, type}]

  // --- Mailgun-related state ---
  const [mailgunUsername, setMailgunUsername] = useState("");
  const [mailgunCachedFiles, setMailgunCachedFiles] = useState([]); // array of {filename,...}
  const [mailgunSelections, setMailgunSelections] = useState({}); // { filename: { type, password } }

  const pollRef = useRef(null);

  // removeStatus state (already present in file)
  const [removeStatus, setRemoveStatus] = useState({}); // { filename: 'removing'|'error'|'done' }

  // Confirm dialog state for removal
  const [confirmRemoveOpen, setConfirmRemoveOpen] = useState(false);
  const [confirmFilename, setConfirmFilename] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function loadMailgunInfo() {
      try {
        const user = await fetchCurrentUser();
        if (!mounted) return;
        setMailgunUsername(user && user.username ? user.username : "");
        const cache = await fetchMailgunCache();
        if (!mounted) return;
        const files = (cache && cache.files) || [];
        setMailgunCachedFiles(files);

        // initialize selections (autodetect type)
        setMailgunSelections((prev) => {
          const next = { ...prev };
          files.forEach((f) => {
            if (!next[f.filename]) {
              next[f.filename] = { type: inferFileType(f.filename) || "", password: "" };
            }
          });
          // remove selections for files no longer present
          Object.keys(next).forEach((k) => {
            if (!files.find((ff) => ff.filename === k)) delete next[k];
          });
          return next;
        });
      } catch (err) {
        console.error("Mailgun load error", err);
      }
    }
    loadMailgunInfo();
    return () => {
      mounted = false;
    };
  }, []);

  // Polling: while Upload Dialog is open (dialogOpen prop) refetch cache every 10s
  useEffect(() => {
    async function refreshCacheOnce() {
      try {
        const cache = await fetchMailgunCache();
        const files = (cache && cache.files) || [];
        setMailgunCachedFiles(files);
        setMailgunSelections((prev) => {
          const next = { ...prev };
          files.forEach((f) => {
            if (!next[f.filename]) {
              next[f.filename] = { type: inferFileType(f.filename) || "", password: "" };
            }
          });
          Object.keys(next).forEach((k) => {
            if (!files.find((ff) => ff.filename === k)) delete next[k];
          });
          return next;
        });
      } catch (err) {
        // ignore
      }
    }

    if (dialogOpen) {
      // immediate refresh and interval every 10s
      refreshCacheOnce();
      pollRef.current = setInterval(refreshCacheOnce, 10000);
      return () => {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      };
    } else {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }
    return () => {};
  }, [dialogOpen]);

  // New handlers for mailgun selections
  const handleMailgunTypeChange = (filename, type) => {
    setMailgunSelections((s) => ({ ...s, [filename]: { ...(s[filename] || {}), type } }));
  };

  const handleMailgunPasswordChange = (filename, value) => {
    // allow only digits up to 6 chars
    const cleaned = (value || "").replace(/\D/g, "").slice(0, 6);
    setMailgunSelections((s) => ({ ...s, [filename]: { ...(s[filename] || {}), password: cleaned } }));
  };

  // whether import button should be active (at least one file has both type && password)
  const canImportSome = Object.keys(mailgunSelections).some((fn) => {
    const sel = mailgunSelections[fn];
    return sel && sel.type && sel.password;
  });

  // import status messaging
  const [importStatus, setImportStatus] = useState(null); // { successCount, errors: [] } or { error: "..." }
  const [importing, setImporting] = useState(false);

  const handleImportCached = async () => {
    const items = Object.entries(mailgunSelections)
      .filter(([, sel]) => sel && sel.type && sel.password)
      .map(([filename, sel]) => ({ filename, password: sel.password, type: sel.type }));
    if (!items.length) return;
    setImporting(true);
    setImportStatus(null);
    try {
      const res = await importMailgunCached(items);
      // res expected: { imported: int, errors: [...] }
      setImportStatus({ successCount: res.imported || 0, errors: res.errors || [] });
      // On success remove entries that were imported (res.imported > 0)
      if (res.imported > 0) {
        // refetch cache to reflect removals
        const cache = await fetchMailgunCache();
        const files = (cache && cache.files) || [];
        setMailgunCachedFiles(files);
        // prune selections
        setMailgunSelections((prev) => {
          const next = { ...prev };
          Object.keys(next).forEach((k) => {
            if (!files.find((ff) => ff.filename === k)) delete next[k];
          });
          return next;
        });

        // Notify parent that imports happened so it can refresh payments (same as file upload)
        if (onSuccess) onSuccess();
      }
    } catch (err) {
      // fetchWithAuth throws Errors with message (could be array or string)
      const msg = err.message || "Import failed";
      setImportStatus({ error: Array.isArray(msg) ? msg : [msg] });
    } finally {
      setImporting(false);
    }
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

  const inferFileType = (fileName) => {
    const lowerName = (fileName || "").toLowerCase();
    if (lowerName.includes("支付宝") || lowerName.includes("alipay")) {
      return "Alipay";
    }
    if (lowerName.includes("微信") || lowerName.includes("wechat")) {
      return "WeChat";
    }
    if (lowerName.includes("tsinghua") || lowerName.includes("card") || fileName.includes("ÓÃ»§½»Ò×¼ÇÂ¼")) {
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

  // Right-click handler -> open ConfirmDialog instead of window.confirm
  const handleContextMenu = (e, filename) => {
    e.preventDefault();
    setConfirmFilename(filename);
    setConfirmRemoveOpen(true);
  };

  // ConfirmDialog confirm handler
  const handleConfirmRemove = async () => {
    const filename = confirmFilename;
    setConfirmRemoveOpen(false);
    if (!filename) return;
    setRemoveStatus((s) => ({ ...s, [filename]: "removing" }));
    try {
      await removeMailgunCacheFile(filename);
      // refresh cache and prune selections
      const cache = await fetchMailgunCache();
      const files = (cache && cache.files) || [];
      setMailgunCachedFiles(files);
      setMailgunSelections((prev) => {
        const next = { ...prev };
        Object.keys(next).forEach((k) => {
          if (!files.find((ff) => ff.filename === k)) delete next[k];
        });
        return next;
      });
      setRemoveStatus((s) => ({ ...s, [filename]: "done" }));
    } catch (err) {
      setRemoveStatus((s) => ({ ...s, [filename]: "error" }));
      setImportStatus({ error: [err.message || "Failed to remove file"] });
    } finally {
      // clear transient removeStatus after a short delay
      setTimeout(() => {
        setRemoveStatus((s) => {
          const copy = { ...s };
          delete copy[filename];
          return copy;
        });
      }, 1800);
    }
  };

  // ConfirmDialog cancel handler
  const handleCancelRemove = () => {
    setConfirmFilename(null);
    setConfirmRemoveOpen(false);
  };

  return (
    <>
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
      {/* --- New: Send files via email container --- */}
      <div className="upload-container" style={{ marginTop: 16 }}>
        <div className="upload-header">
          <div className="upload-icon">✉️</div>
          <div className="upload-header-text">
            <h3>Send files via email</h3>
            <p>
                When exporting the payment information in WeChat or AliPay, select send to E-Mail. <br />
                Enter your custom PayFlow E-Mail address as recipient. <br />
                To import the file, enter the files password.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8 }}>
          <div style={{ flex: 1 }}>
            <div style={{ marginBottom: 8, fontSize: 14, color: "#333", fontWeight: 600 }}>
              Your custom email
            </div>
            <div style={{ padding: "8px 12px", background: "#f6f8fb", borderRadius: 8, display: "inline-block", fontFamily: "monospace" }}>
              {mailgunUsername ? `${mailgunUsername}@payflow.darpey.de` : "Loading..."}
            </div>
          </div>

          {/* Import button next to custom email */}
          <div style={{ display: "flex", alignItems: "center" }}>
            <button
              className="upload-btn"
              onClick={handleImportCached}
              disabled={!canImportSome || importing}
              type="button"
            >
              <span className="upload-btn-icon">⬇️</span>
              <span>{importing ? "Importing..." : "Import Selected"}</span>
            </button>
          </div>
        </div>

        <div style={{ marginTop: 16 }}>
          <div style={{ marginBottom: 8, fontSize: 14, color: "#333", fontWeight: 600 }}>
            Received files
          </div>
          {mailgunCachedFiles.length === 0 ? (
            <div style={{ color: "rgba(0,0,0,0.5)" }}>No cached files</div>
          ) : (
            <div className="file-list" style={{ marginTop: 8 }}>
              {mailgunCachedFiles.map((f) => {
                const sel = mailgunSelections[f.filename] || { type: "", password: "" };
                return (
                  <div
                    key={f.filename}
                    className="file-item"
                    style={{ alignItems: "center", display: "flex", gap: 12 }}
                    title="Right-click to remove file"               // <-- tooltip on hover
                    onContextMenu={(e) => handleContextMenu(e, f.filename)} // <-- right-click handler
                  >
                    <div className="file-icon">📄</div>
                    <div className="file-info" style={{ minWidth: 0, flex: 1 }}>
                      <p className="file-name" style={{ marginBottom: 6 }}>{f.filename}</p>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <select
                          className={`file-type-select ${!sel.type ? 'empty' : ''}`}
                          value={sel.type}
                          onChange={e => handleMailgunTypeChange(f.filename, e.target.value)}
                          disabled={importing}
                        >
                          <option value="">Select Type</option>
                          {paymentSourceOptions.map(opt => (
                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                          ))}
                        </select>
                        <input
                          type="text"
                          inputMode="numeric"
                          pattern="\d*"
                          maxLength={6}
                          placeholder="Password (max 6 digits)"
                          value={sel.password}
                          onChange={e => handleMailgunPasswordChange(f.filename, e.target.value)}
                          style={{
                            padding: "10px 12px",
                            borderRadius: "8px",
                            border: "1px solid rgba(0,0,0,0.08)",
                            minWidth: 160,
                          }}
                          disabled={importing}
                        />
                      </div>
                    </div>
                    <div style={{ width: 120, textAlign: "right" }}>
                      {/* show a small indicator if this file is ready to import */}
                      {removeStatus[f.filename] === "removing" ? (
                        <div style={{ color: "#f59e0b", fontWeight: 700 }}>Removing...</div>
                      ) : removeStatus[f.filename] === "error" ? (
                        <div style={{ color: "#dc2626", fontWeight: 700 }}>Remove failed</div>
                      ) : sel.type && sel.password ? (
                        <div style={{ color: "#059669", fontWeight: 700 }}>Ready</div>
                      ) : (
                        <div style={{ color: "rgba(0,0,0,0.4)" }}>Incomplete</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Import result */}
        {importStatus && (
          <div style={{ marginTop: 12 }}>
            {importStatus.error ? (
              <div className="error-message">
                <span className="error-icon">⚠️</span>
                <div>
                  <div style={{ fontWeight: 700 }}>Import failed</div>
                  {Array.isArray(importStatus.error) ? (
                    importStatus.error.map((e, i) => <div key={i}>{String(e)}</div>)
                  ) : (
                    <div>{String(importStatus.error)}</div>
                  )}
                </div>
              </div>
            ) : (
              <div className="success-list">
                <div className="success-item">
                  <span className="success-icon">✓</span>
                  <span>{`Imported ${importStatus.successCount} file(s)`}</span>
                </div>
                {importStatus.errors && importStatus.errors.length > 0 && (
                  <div style={{ marginTop: 8, color: "#dc2626", fontWeight: 700 }}>
                    Errors:
                    <ul>
                      {importStatus.errors.map((err, idx) => <li key={idx}>{err}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Confirm dialog for removing cached file */}
      <ConfirmDialog
        open={confirmRemoveOpen}
        onClose={handleCancelRemove}
        onConfirm={handleConfirmRemove}
        title="Remove cached file"
        description={confirmFilename ? `Remove cached file "${confirmFilename}"? This will delete the cached upload.` : "Remove cached file?"}
        confirmText="Remove"
        cancelText="Cancel"
        loading={removeStatus[confirmFilename] === "removing"}
      />
    </>
  );
}
