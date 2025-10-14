import { useState, useEffect } from "react";
import {fetchCategories, fetchCategoryTree, updateCategoryTree, updatePaymentCategory, allMerchantSameCategory} from "../api";
import { useSnackbar } from "notistack";
import ConfirmDialog from "../components/ConfirmDialog";

export function useCategories(refetchPayments) {
  const [categories, setCategories] = useState([]);
  const [categoryTree, setCategoryTree] = useState({});
  const [managerOpen, setManagerOpen] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  // Dialog state for category change confirmation
  const [confirmCategoryDialog, setConfirmCategoryDialog] = useState({
    open: false,
    payment: null,
    newCat: "",
    payments: [],
    setPayments: null,
    onConfirm: null,
  });

  // Fetch categories and category tree on mount
  useEffect(() => {
    fetchCategoryTree()
      .then(setCategoryTree)
      .catch(() => setCategoryTree({}));
    fetchCategories()
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  // Update category tree
  const handleUpdateCategoryTree = (newTree) => {
    updateCategoryTree(newTree)
      .then(() => {
        setCategoryTree(newTree);
        enqueueSnackbar && enqueueSnackbar("Categories updated", { variant: "success" });
        if (refetchPayments) refetchPayments();
      })
      .catch(() => {
        enqueueSnackbar && enqueueSnackbar("Failed to update categories", { variant: "error" });
      });
    fetchCategories()
      .then(setCategories)
      .catch(() => setCategories([]));
  };

  // Helper to check if all merchant's transactions have the same category (backend)
  const checkAllMerchantSameCategory = async (merchant, currentCat) => {
    try {
      const res = await allMerchantSameCategory(merchant, currentCat);
      return res.all_same;
    } catch {
      return false;
    }
  };

  // Update category (with ConfirmDialog)
  const handleCategoryChange = async (payment, newCat, payments, setPayments) => {
    const allSame = await checkAllMerchantSameCategory(payment.merchant, payment.cust_category);
    if (allSame) {
      setConfirmCategoryDialog({
        open: true,
        payment,
        newCat,
        payments,
        setPayments,
        onConfirm: async () => {
          await updatePaymentCategory(payment.id, newCat, true);
          setPayments(payments =>
            payments.map(p =>
              p.merchant === payment.merchant ? { ...p, cust_category: newCat } : p
            )
          );
          setConfirmCategoryDialog(dialog => ({ ...dialog, open: false }));
        }
      });
      return;
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

  // ConfirmDialog component for category change
  const CategoryConfirmDialog = () => (
    <ConfirmDialog
      open={confirmCategoryDialog.open}
      onClose={() => setConfirmCategoryDialog(dialog => ({ ...dialog, open: false }))}
      onConfirm={confirmCategoryDialog.onConfirm}
      title="Change All Merchant Categories?"
      description="Change all categories of that merchant's transactions? This action cannot be undone."
      confirmText="Change All"
      cancelText="Cancel"
    />
  );

  return {
    categories,
    categoryTree,
    managerOpen,
    setManagerOpen,
    handleUpdateCategoryTree,
    handleCategoryChange,
    CategoryConfirmDialog
  };
}