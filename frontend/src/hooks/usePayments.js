import { useState, useEffect } from "react";
import { fetchPayments } from "../api";

export function usePayments({ page = 1, pageSize = 50, search = "" } = {}) {
  const [payments, setPayments] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [currentPage, setCurrentPage] = useState(page);
  const [currentSearch, setCurrentSearch] = useState(search);

  // Update currentSearch when parent search changes
  useEffect(() => {
    setCurrentSearch(search);
  }, [search]);

  const refetchPayments = async (opts = {}) => {
    setLoading(true);
    try {
      const res = await fetchPayments({
        page: opts.page ?? currentPage,
        pageSize: opts.pageSize ?? pageSize,
        search: opts.search ?? currentSearch,
      });
      setPayments(res.payments);
      setTotal(res.total);
      setLoading(false);
    } catch (e) {
      setError(e.message || "Failed to fetch payments");
      setLoading(false);
    }
  };

  useEffect(() => {
    refetchPayments({ page: currentPage, search: currentSearch });
    // eslint-disable-next-line
  }, [currentPage, currentSearch, pageSize]);

  return {
    payments,
    setPayments,
    loading,
    error,
    total,
    page: currentPage,
    setPage: setCurrentPage,
    search: currentSearch,
    setSearch: setCurrentSearch,
    refetchPayments,
  };
}
