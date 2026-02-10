import React from "react";
import { Grid, Card, CardContent, Typography, CircularProgress } from "@mui/material";
import { format } from "date-fns";
import { fetchSumsForRanges } from "../api";

// Format sum as negative, integer, add currency symbol, and use K notation if >= 10000
function formatSum(sum, currency) {
  const abs = Math.abs(Math.round(sum));
  let display;
  let symbol = "元";
  if (currency === "USD") symbol = "$";
  else if (currency === "EUR") symbol = "€";
  if (currency !== "CNY") symbol = currency;
  if (abs >= 10000) {
    display = `${(abs / 1000).toFixed(1)}K ${symbol}`;
  } else {
    display = `${abs} ${symbol}`;
  }
  return `${display}`;
}

export default function SummaryCards({ dateRange, setDateRange, onAggregate, summaryRefreshKey, setSummaryRefreshKey }) {
  // Get currency from localStorage, default to CNY
  const currency = (typeof window !== "undefined" && localStorage.getItem("currency")) || "CNY";

  // State for summary data and loading
  const [summary, setSummary] = React.useState({
    total: -1,
    past7: 0,
    past30: 0,
    custom: 0,
    pastMonth: 0,
    currentMonth: 0,
    currentMonthEstimate: 0,
    totalStart: null,
    totalEnd: null,
    past7Start: null,
    past7End: null,
    past30Start: null,
    past30End: null,
    pastMonthStart: null,
    pastMonthEnd: null,
    currentMonthStart: null,
    currentMonthEnd: null,
    customStart: null,
    customEnd: null,
  });
  const [loading, setLoading] = React.useState(true);

  // Helper for naive ISO string
  const toNaiveISOString = (d) => d ? d.toISOString().slice(0, 19) : null;

  React.useEffect(() => {
    setLoading(true);

    if (dateRange && dateRange[0] && dateRange[1]) {
      const ranges = {
        custom: {
          start: toNaiveISOString(dateRange[0]),
          end: toNaiveISOString(dateRange[1]),
        }
      };
      fetchSumsForRanges(ranges)
        .then((res) => setSummary((prev) => ({
          ...prev,
          custom: res.custom?.sum ?? 0,
          customStart: res.custom?.start_date ? new Date(res.custom.start_date) : null,
          customEnd: res.custom?.end_date ? new Date(res.custom.end_date) : null,
        })))
        .catch(() => {})
        .finally(() => setLoading(false));
      return;
    }

    // Use months param for current and past month
    const ranges = {
      total: { start: null, end: null },
      past7: { days: 7 },
      past30: { days: 30 },
      currentMonth: { months: 0 },
      pastMonth: { months: 1 },
    };

    fetchSumsForRanges(ranges)
      .then((res) => {
        // Calculate currentMonthEstimate based on days between start and end date
        let estimate = 0;
        if (res.currentMonth?.sum != null && res.currentMonth?.start_date && res.currentMonth?.end_date) {
          const startDate = new Date(res.currentMonth.start_date);
          const endDate = new Date(res.currentMonth.end_date);
          if (
            startDate.getFullYear() === endDate.getFullYear() &&
            startDate.getMonth() === endDate.getMonth()
          ) {
            const daysInMonth = new Date(startDate.getFullYear(), startDate.getMonth() + 1, 0).getDate();
            const daysPassed = Math.max(1, Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24)) + 1);
            const avgPerDay = res.currentMonth.sum / daysPassed;
            estimate = avgPerDay * daysInMonth;
          }
        }
        setSummary((prev) => ({
          ...prev,
          total: res.total?.sum ?? 0,
          totalStart: res.total?.start_date ? new Date(res.total.start_date) : null,
          totalEnd: res.total?.end_date ? new Date(res.total.end_date) : null,
          past7: res.past7?.sum ?? 0,
          past30: res.past30?.sum ?? 0,
          past7Start: res.past7?.start_date ? new Date(res.past7.start_date) : null,
          past7End: res.past7?.end_date ? new Date(res.past7.end_date) : null,
          past30Start: res.past30?.start_date ? new Date(res.past30.start_date) : null,
          past30End: res.past30?.end_date ? new Date(res.past30.end_date) : null,
          pastMonth: res.pastMonth?.sum ?? 0,
          pastMonthStart: res.pastMonth?.start_date ? new Date(res.pastMonth.start_date) : null,
          pastMonthEnd: res.pastMonth?.end_date ? new Date(res.pastMonth.end_date) : null,
          currentMonth: res.currentMonth?.sum ?? 0,
          currentMonthStart: res.currentMonth?.start_date ? new Date(res.currentMonth.start_date) : null,
          currentMonthEnd: res.currentMonth?.end_date ? new Date(res.currentMonth.end_date) : null,
          custom: prev.custom,
          customStart: prev.customStart,
          customEnd: prev.customEnd,
          currentMonthEstimate: estimate, // <-- set the value here
        }));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [dateRange, summaryRefreshKey]);

  // Handler for card click, triggers aggregation
  const handleCardClick = ({ type, start, end, days }) => {
    if (onAggregate) {
      onAggregate({ type, start, end, days });
    }
  };

  // Compose all cards with their sums and render info
  const cards = [
    {
      key: "total",
      label: "Total Expenses",
      sum: summary.total,
      caption:
        summary.totalStart && summary.totalEnd
          ? `${format(summary.totalStart, "MMM d")} – ${format(summary.totalEnd, "MMM d, yyyy")}`
          : "",
      gradient: "linear-gradient(135deg, #111827, #1f2937)",
      onClick: () => handleCardClick({ type: "total", start: null, end: null }),
    },
    {
      key: "past7",
      label: "Past 7 Days",
      sum: summary.past7,
      caption:
        summary.past7Start && summary.past7End
          ? `${format(summary.past7Start, "MMM d")} – ${format(summary.past7End, "MMM d, yyyy")}`
          : "",
      gradient: "linear-gradient(135deg, #be185d, #f472b6)",
      onClick: () => handleCardClick({ type: "past7", start: null, end: null, days: 7 }),
    },
    {
      key: "past30",
      label: "Past 30 Days",
      sum: summary.past30,
      caption:
        summary.past30Start && summary.past30End
          ? `${format(summary.past30Start, "MMM d")} – ${format(summary.past30End, "MMM d, yyyy")}`
          : "",
      gradient: "linear-gradient(135deg, #f59e42, #fbbf24)",
      onClick: () => handleCardClick({ type: "past30", start: null, end: null, days: 30 }),
    },
    {
      key: "pastMonth",
      label: "Past Month",
      sum: summary.pastMonth,
      caption:
        summary.pastMonthStart
          ? `${format(summary.pastMonthStart, "MMM yyyy")}`
          : "",
      gradient: "linear-gradient(135deg, #6366f1, #818cf8)",
      onClick: () =>
        handleCardClick({
          type: "custom",
          start: summary.pastMonthStart,
          end: summary.pastMonthEnd,
        }),
    },
    {
      key: "currentMonth",
      label: "Current Month",
      sum: summary.currentMonth,
      caption:
        summary.currentMonthEstimate
          ? `Total Estimate: ${formatSum(summary.currentMonthEstimate, currency)}`
          : "",
      gradient: "linear-gradient(135deg, #06b6d4, #3b82f6)",
      onClick: () =>
        handleCardClick({
          type: "custom",
          start: summary.currentMonthStart,
          end: summary.currentMonthEnd,
        }),
    },
  ];

  // Only add custom card if custom range is set
  if (dateRange && dateRange[0] && dateRange[1]) {
    cards.push({
      key: "custom",
      label: "Custom Range",
      sum: summary.custom,
      caption: `${format(dateRange[0], "MMM d")} – ${format(dateRange[1], "MMM d, yyyy")}`,
      gradient: "linear-gradient(135deg, #0ea5e9, #38bdf8)",
      onClick: () => handleCardClick({ type: "custom", start: dateRange[0], end: dateRange[1] }),
    });
  }

  // Sort cards by sum descending
  const sortedCards = [...cards].sort((a, b) => a.sum - b.sum);

  if (loading) {
    return (
      <div className="loading-container" style={{ height: "120px", marginBottom: 24 }}>
        <div className="loading-spinner">
          <CircularProgress size={48} thickness={3.5} sx={{ color: '#667eea' }} />
        </div>
        <Typography className="loading-text">
          Loading summary cards…
        </Typography>
      </div>
    );
  }

  return (
    <Grid container spacing={2} sx={{ mb: 3 }}>
      {sortedCards.map(card => (
        <Grid item xs={12} md={4} lg={2} key={card.key}>
          <Card
            elevation={0}
            sx={{
              borderRadius: 3,
              p: 0.5,
              background: card.gradient,
              color: "white",
              cursor: "pointer",
              transition: "transform 0.18s cubic-bezier(.4,2,.6,1), box-shadow 0.18s cubic-bezier(.4,2,.6,1)",
              "&:hover": {
                transform: "scale(1.045)",
                boxShadow: "0 6px 24px 0 rgba(0,0,0,0.12)",
              }
            }}
            onClick={card.onClick}
          >
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="overline" sx={{ opacity: 0.9 }}>
                {card.label}
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>
                {formatSum(card.sum, currency)}
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.9 }}>
                {card.caption}
              </Typography>
              {card.subtext && (
                <Typography variant="caption" sx={{ opacity: 0.8, display: "block", mt: 0.5 }}>
                  {card.subtext}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}