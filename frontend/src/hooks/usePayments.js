import { useState, useEffect } from "react";
import { fetchPayments } from "../api";

export function usePayments() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refetchPayments = () => {
    setLoading(true);
    fetchPayments()
      .then(data => setPayments(data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refetchPayments();
    // eslint-disable-next-line
  }, []);

  return { payments, setPayments, loading, error, refetchPayments };
}
