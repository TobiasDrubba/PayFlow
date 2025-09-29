import { useState, useEffect } from "react";
import {fetchCategories, fetchCategoryTree, updateCategoryTree, updatePaymentCategory} from "../api";
import { useSnackbar } from "notistack";

export function useCategories() {
  const [categories, setCategories] = useState([]);
  const [categoryTree, setCategoryTree] = useState({});
  const [managerOpen, setManagerOpen] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  // Fetch categories and category tree on mount
  useEffect(() => {
    fetchCategories()
      .then(setCategories)
      .catch(() => setCategories([]));
    fetchCategoryTree()
      .then(setCategoryTree)
      .catch(() => setCategoryTree({}));
  }, []);

  // Update category tree
  const handleUpdateCategoryTree = (newTree) => {
    updateCategoryTree(newTree)
      .then(() => {
        setCategoryTree(newTree);
        enqueueSnackbar && enqueueSnackbar("Categories updated", { variant: "success" });
      })
      .catch(() => {
        enqueueSnackbar && enqueueSnackbar("Failed to update categories", { variant: "error" });
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
    categoryTree,
    managerOpen,
    setManagerOpen,
    handleUpdateCategoryTree,
    handleCategoryChange
  };
}