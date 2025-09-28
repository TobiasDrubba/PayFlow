import { useState, useEffect } from "react";
import { fetchCategories, addCategory, updatePaymentCategory } from "../api";
import { useSnackbar } from "notistack";

export function useCategories() {
  const [categories, setCategories] = useState([]);
  const [addCatOpen, setAddCatOpen] = useState(false);
  const [newCat, setNewCat] = useState("");
  const { enqueueSnackbar } = useSnackbar();

  // Fetch categories on mount
  useEffect(() => {
    fetchCategories()
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  // Add new category
  const handleAddCategory = () => {
    addCategory(newCat)
      .then(cat => {
        setCategories(prev => [...prev, cat]);
        setAddCatOpen(false);
        setNewCat("");
        enqueueSnackbar && enqueueSnackbar("Category added", { variant: "success" });
      })
      .catch(() => {
        enqueueSnackbar && enqueueSnackbar("Failed to add category", { variant: "error" });
      });
  };

  // Helper to check if all merchant's transactions have the same category
  const allMerchantSameCategory = (merchant, currentCat, payments) => {
    const txs = payments.filter(p => p.merchant === merchant);
    return txs.length > 1 && txs.every(p => p.cust_category === currentCat);
  };

  // Update category (with prompt)
  const handleCategoryChange = (payment, newCat, payments, setPayments) => {
    if (allMerchantSameCategory(payment.merchant, payment.cust_category, payments)) {
      if (window.confirm("Change all categories of that merchant's transaction?")) {
        // Bulk update
        updatePaymentCategory(payment.id, newCat, true).then(() => {
          setPayments(payments =>
            payments.map(p =>
              p.merchant === payment.merchant ? { ...p, cust_category: newCat } : p
            )
          );
        });
        return;
      }
    }
    // Single update
    updatePaymentCategory(payment.id, newCat, false).then(() => {
      setPayments(payments =>
        payments.map(p =>
          p.id === payment.id ? { ...p, cust_category: newCat } : p
        )
      );
    });
  };

  return {
    categories,
    addCatOpen,
    setAddCatOpen,
    newCat,
    setNewCat,
    handleAddCategory,
    handleCategoryChange
  };
}