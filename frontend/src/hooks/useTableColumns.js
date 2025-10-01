import { useState, useEffect, useMemo } from "react";

export function useTableColumns() {
  const allColumns = useMemo(() => ([
    { id: "date", label: "Date" },
    { id: "amount", label: "Amount", align: "right" },
    { id: "currency", label: "Currency" },
    { id: "merchant", label: "Merchant" },
    { id: "auto_category", label: "Auto Category" },
    { id: "source", label: "Source" },
    { id: "type", label: "Type" },
    { id: "note", label: "Note" },
    { id: "cust_category", label: "Category" },
  ]), []);

  const [columnOrder, setColumnOrder] = useState(() => {
    const saved = localStorage.getItem("paymentsTable.columnOrder");
    return saved ? JSON.parse(saved) : allColumns.map(c => c.id);
  });

  const [visibleColumns, setVisibleColumns] = useState(() => {
    const saved = localStorage.getItem("paymentsTable.visibleColumns");
    return new Set(saved ? JSON.parse(saved) : allColumns.map(c => c.id));
  });

  useEffect(() => {
    localStorage.setItem("paymentsTable.columnOrder", JSON.stringify(columnOrder));
  }, [columnOrder]);

  useEffect(() => {
    localStorage.setItem("paymentsTable.visibleColumns", JSON.stringify(Array.from(visibleColumns)));
  }, [visibleColumns]);

  const orderedColumns = useMemo(
    () => columnOrder.map(id => allColumns.find(c => c.id === id)).filter(Boolean),
    [columnOrder, allColumns]
  );

  const toggleColumn = (id) => {
    setVisibleColumns(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        // keep at least one column visible
        if (next.size > 1) next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const onDragEnd = (result) => {
    if (!result.destination) return;
    const srcIdx = result.source.index;
    const dstIdx = result.destination.index;
    setColumnOrder(prev => {
      const next = [...prev];
      const [moved] = next.splice(srcIdx, 1);
      next.splice(dstIdx, 0, moved);
      return next;
    });
  };

  return {
    allColumns,
    orderedColumns,
    visibleColumns,
    toggleColumn,
    onDragEnd
  };
}