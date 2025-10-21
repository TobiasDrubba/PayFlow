import React, { useEffect, useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Box, TextField, DialogContentText, IconButton, List, ListItem, ListItemText, Collapse, Tooltip, Zoom, Menu, MenuItem
} from "@mui/material";
import { Add, ExpandLess, ExpandMore } from "@mui/icons-material";
import "./ManageCategoriesDialog.css";

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

// Helper to deep clone the tree
function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

// Helper to delete a key in the tree by path
function deleteTreeKey(tree, path) {
  if (path.length === 1) {
    delete tree[path[0]];
    return;
  }
  deleteTreeKey(tree[path[0]], path.slice(1));
  if (Object.keys(tree[path[0]]).length === 0) {
    tree[path[0]] = null;
  }
}

// Helper to rename a key in the tree by path
function renameTreeKey(tree, path, newName) {
  if (path.length === 1) {
    tree[newName] = tree[path[0]];
    delete tree[path[0]];
    return;
  }
  renameTreeKey(tree[path[0]], path.slice(1), newName);
}

export default function ManageCategoriesDialog({
  open,
  onClose,
  categoryTree,
  onUpdate,
  payments = []
}) {
  const [tree, setTree] = useState(deepClone(categoryTree));
  const [expanded, setExpanded] = useState({});
  const [editPath, setEditPath] = useState(null);
  const [editValue, setEditValue] = useState("");
  const [addPath, setAddPath] = useState(null);
  const [addValue, setAddValue] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deletedCategories, setDeletedCategories] = useState([]);
  const [affectedPayments, setAffectedPayments] = useState([]);
  const [contextMenu, setContextMenu] = useState(null);
  const [contextPath, setContextPath] = useState(null);
  const [contextName, setContextName] = useState("");

  useEffect(() => {
    setTree(deepClone(categoryTree));
    setExpanded({});
    setEditPath(null);
    setAddPath(null);
    setEditValue("");
    setAddValue("");
  }, [categoryTree, open]);

  const handleExpand = (pathStr) => {
    setExpanded(prev => ({ ...prev, [pathStr]: !prev[pathStr] }));
  };

  const handleEditSave = () => {
    if (!editValue.trim()) return;
    const newTree = deepClone(tree);
    renameTreeKey(newTree, editPath, editValue.trim());
    setTree(newTree);
    setEditPath(null);
    setEditValue("");
  };

  const handleAddSave = () => {
    if (!addValue.trim()) return;
    const newTree = deepClone(tree);

    // Traverse to parent, but keep track of the path for fixing null->object
    let parent = newTree;
    let parentRefs = [newTree];
    for (const key of addPath) {
      parent = parent[key];
      parentRefs.push(parent);
    }

    // If parent is not an object (i.e. null), convert it to an object in the actual tree
    if (!parent || typeof parent !== "object") {
      // Traverse again and set the last key to {}
      let obj = newTree;
      for (let i = 0; i < addPath.length - 1; i++) {
        obj = obj[addPath[i]];
      }
      obj[addPath[addPath.length - 1]] = {};
      parent = obj[addPath[addPath.length - 1]];
    }

    parent[addValue.trim()] = null;

    // --- Fix: auto-expand parent when adding first child ---
    if (addPath.length > 0) {
      const parentPathStr = addPath.join(">");
      setExpanded(prev => ({ ...prev, [parentPathStr]: true }));
    }
    // -------------------------------------------------------

    setTree(newTree);
    setAddPath(null);
    setAddValue("");
  };

  const handleDelete = (path) => {
    const oldChildCats = getAllChildCategories(tree);
    const newTree = deepClone(tree);
    deleteTreeKey(newTree, path);
    const newChildCats = getAllChildCategories(newTree);
    const deleted = oldChildCats.filter(cat => !newChildCats.includes(cat));
    if (deleted.length > 0 && payments.length > 0) {
      const affected = payments.filter(p => deleted.includes(p.cust_category));
      if (affected.length > 0) {
        setDeletedCategories(deleted);
        setAffectedPayments(affected);
        setConfirmOpen({ path, newTree });
        return;
      }
    }
    setTree(newTree);
  };

  const handleConfirm = () => {
    setTree(confirmOpen.newTree);
    setConfirmOpen(false);
    setDeletedCategories([]);
    setAffectedPayments([]);
  };

  const handleCancelConfirm = () => {
    setConfirmOpen(false);
    setDeletedCategories([]);
    setAffectedPayments([]);
  };

  const handleSave = () => {
    onUpdate(tree);
    onClose();
  };

  const handleMainCancel = () => {
    setTree(deepClone(categoryTree));
    setEditPath(null);
    setAddPath(null);
    setEditValue("");
    setAddValue("");
    onClose();
  };

  // Context menu handlers
  const handleCategoryRightClick = (event, path, name) => {
    event.preventDefault();
    setContextMenu(
      contextMenu === null
        ? {
            mouseX: event.clientX - 2,
            mouseY: event.clientY - 4,
          }
        : null,
    );
    setContextPath(path);
    setContextName(name);
  };

  const handleCloseContextMenu = () => {
    setContextMenu(null);
    setContextPath(null);
    setContextName("");
  };

  // Edit from context menu
  const handleContextEdit = () => {
    setEditPath(contextPath);
    setEditValue(contextName);
    handleCloseContextMenu();
  };

  // Add child from context menu
  const handleContextAddChild = () => {
    setAddPath(contextPath);
    setAddValue("");
    handleCloseContextMenu();
  };

  // Delete from context menu
  const handleContextDelete = () => {
    handleDelete(contextPath);
    handleCloseContextMenu();
  };

  // Render the indented list recursively
  function renderTree(node, level = 0, parentPath = []) {
    return Object.entries(node).map(([key, value]) => {
      const path = [...parentPath, key];
      const pathStr = path.join(">");
      const isEditing = editPath && JSON.stringify(editPath) === JSON.stringify(path);
      const isAdding = addPath && JSON.stringify(addPath) === JSON.stringify(path);
      const hasChildren = value && typeof value === "object" && Object.keys(value).length > 0;
      const isSelected = contextPath && JSON.stringify(contextPath) === JSON.stringify(path);
      return (
        <React.Fragment key={pathStr}>
          <ListItem
            className={`category-item${isSelected ? " selected" : ""}`}
            sx={{ pl: 2 + level * 3 }}
            onContextMenu={e => handleCategoryRightClick(e, path, key)}
            selected={isSelected}
          >
            {hasChildren ? (
              <Tooltip title={expanded[pathStr] ? "Collapse" : "Expand"} arrow>
                <IconButton size="small" onClick={() => handleExpand(pathStr)}>
                  {expanded[pathStr] ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
              </Tooltip>
            ) : (
              <Box sx={{ width: 40, display: "inline-block" }} />
            )}
            {isEditing ? (
              <Zoom in>
                <Box className="edit-box">
                  <TextField
                    value={editValue}
                    onChange={e => setEditValue(e.target.value)}
                    size="small"
                    sx={{ width: 180, mr: 1 }}
                    autoFocus
                    onKeyDown={e => {
                      if (e.key === "Enter") handleEditSave();
                    }}
                  />
                  <Button onClick={handleEditSave} size="small" variant="contained" color="success" className="btn-save">Save</Button>
                  <Button onClick={() => setEditPath(null)} size="small" color="secondary" className="btn-cancel">Cancel</Button>
                </Box>
              </Zoom>
            ) : (
              <>
                <ListItemText
                  primary={
                    <span className="category-name">
                      {key}
                    </span>
                  }
                />
              </>
            )}
          </ListItem>
          {isAdding && (
            <ListItem sx={{ pl: 2 + (level + 1) * 3 }} className="add-item">
              <TextField
                value={addValue}
                onChange={e => setAddValue(e.target.value)}
                size="small"
                sx={{ width: 180, mr: 1 }}
                autoFocus
                placeholder="New subcategory"
                onKeyDown={e => {
                  if (e.key === "Enter") handleAddSave();
                }}
              />
              <Button onClick={handleAddSave} size="small" variant="contained" color="primary" className="btn-save">Add</Button>
              <Button onClick={() => setAddPath(null)} size="small" color="secondary" className="btn-cancel">Cancel</Button>
            </ListItem>
          )}
          {hasChildren && (
            <Collapse in={expanded[pathStr]} timeout="auto" unmountOnExit>
              {renderTree(value, level + 1, path)}
            </Collapse>
          )}
        </React.Fragment>
      );
    });
  }

  return (
    <>
      <Dialog open={open} onClose={handleMainCancel} maxWidth="md" fullWidth>
        <DialogTitle>
          <span className="dialog-title">Manage Categories</span>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ height: 500, overflowY: "auto", position: "relative" }}>
            <List>
              {renderTree(tree)}
              {/* Add new root category */}
              {addPath === null && (
                <ListItem className="add-root" sx={{ background: "transparent", marginBottom: 0, display: "flex", alignItems: "center" }}>
                  <Button
                    startIcon={<Add />}
                    onClick={() => setAddPath([])}
                    variant="contained"
                    color="primary"
                  >
                    Add Root Category
                  </Button>
                  <span className="right-click-hint">
                    right click category to view options
                  </span>
                </ListItem>
              )}
              {addPath && addPath.length === 0 && (
                <ListItem className="add-item">
                  <TextField
                    value={addValue}
                    onChange={e => setAddValue(e.target.value)}
                    size="small"
                    sx={{ width: 180, mr: 1 }}
                    autoFocus
                    placeholder="New root category"
                    onKeyDown={e => {
                      if (e.key === "Enter") {
                        const newTree = deepClone(tree);
                        newTree[addValue.trim()] = null;
                        setTree(newTree);
                        setAddPath(null);
                        setAddValue("");
                      }
                    }}
                  />
                  <Button
                    onClick={() => {
                      if (!addValue.trim()) return;
                      const newTree = deepClone(tree);
                      newTree[addValue.trim()] = null;
                      setTree(newTree);
                      setAddPath(null);
                      setAddValue("");
                    }}
                    size="small"
                    variant="contained"
                    color="primary"
                  >
                    Add
                  </Button>
                  <Button onClick={() => setAddPath(null)} size="small" color="secondary" className="btn-cancel">Cancel</Button>
                </ListItem>
              )}
            </List>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleMainCancel} color="secondary" className="btn-cancel">Cancel</Button>
          <Button variant="contained" color="success" onClick={handleSave} className="btn-save">
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>
      {/* Context menu for category actions */}
      <Menu
        open={contextMenu !== null}
        onClose={handleCloseContextMenu}
        anchorReference="anchorPosition"
        anchorPosition={
          contextMenu !== null
            ? { top: contextMenu.mouseY, left: contextMenu.mouseX }
            : undefined
        }
      >
        <MenuItem onClick={handleContextEdit}>Edit</MenuItem>
        <MenuItem onClick={handleContextAddChild}>Add Child Category</MenuItem>
        <MenuItem onClick={handleContextDelete}>Delete</MenuItem>
      </Menu>
      <Dialog open={!!confirmOpen} onClose={handleCancelConfirm}>
        <DialogTitle>Confirm Category Deletion</DialogTitle>
        <DialogContent>
          <DialogContentText>
            <span className="confirm-text">
              The following categories will be removed:
              <ul>
                {deletedCategories.map(cat => (
                  <li key={cat}><b>{cat}</b></li>
                ))}
              </ul>
              {affectedPayments.length > 0 && (
                <>
                  <b>{affectedPayments.length}</b> payment(s) use these categories and will become uncategorized.<br />
                  Are you sure you want to proceed?
                </>
              )}
            </span>
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelConfirm} color="secondary" className="btn-cancel">Cancel</Button>
          <Button variant="contained" color="error" onClick={handleConfirm} className="btn-delete">
            Yes, update and uncategorize payments
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}