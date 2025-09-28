import { useState, useEffect, useMemo } from "react";
import { fetchPayments } from "../api";
import { isWithinInterval, startOfMonth, endOfMonth } from "date-fns";

export function usePayments() {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPayments()
      .then(data => setPayments(data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return { payments, setPayments, loading, error };
}

export function usePaymentSums(payments, dateRange) {
  const isPositive = (t) => t === "income" || t === "refund";
  const isAbort = (t) => t === "abort";

  const totalSum = useMemo(
    () =>
      payments.reduce((sum, p) => {
        const t = p.type?.toLowerCase();
        if (isAbort(t)) return sum;
        const sign = isPositive(t) ? 1 : -1;
        return sum + sign * (Math.abs(p.amount) || 0);
      }, 0),
    [payments]
  );

  const now = useMemo(() => new Date(), []);

  const monthlySum = useMemo(
    () =>
      payments
        .filter(p =>
          !isAbort(p.type?.toLowerCase()) &&
          isWithinInterval(new Date(p.date), {
            start: startOfMonth(now),
            end: endOfMonth(now),
          })
        )
        .reduce((sum, p) => {
          const t = p.type?.toLowerCase();
          const sign = isPositive(t) ? 1 : -1;
          return sum + sign * (Math.abs(p.amount) || 0);
        }, 0),
    [payments, now]
  );

  const customSum = useMemo(() => {
    if (!dateRange[0] || !dateRange[1]) return 0;
    return payments
      .filter(p =>
        !isAbort(p.type?.toLowerCase()) &&
        isWithinInterval(new Date(p.date), {
          start: dateRange[0],
          end: dateRange[1],
        })
      )
      .reduce((sum, p) => {
        const t = p.type?.toLowerCase();
        const sign = isPositive(t) ? 1 : -1;
        return sum + sign * (Math.abs(p.amount) || 0);
      }, 0);
  }, [payments, dateRange]);

  return { totalSum, monthlySum, customSum, now };
}