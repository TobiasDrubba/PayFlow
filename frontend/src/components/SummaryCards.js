import React from "react";
import { Grid, Card, CardContent, Typography } from "@mui/material";
import { format } from "date-fns";

// Format sum as negative, integer, add currency symbol, and use K notation if >= 10000
function formatSum(sum, currency) {
  const abs = Math.abs(Math.round(sum));
  let display;
  let symbol = "元";
  if (currency === "USD") symbol = "$";
  else if (currency === "EUR") symbol = "€";
  if (abs >= 10000) {
    display = `${(abs / 1000).toFixed(1)}K ${symbol}`;
  } else {
    display = `${abs} ${symbol}`;
  }
  return `${display}`;
}

export default function SummaryCards({
  totalSum,
  customSum,
  dateRange,
  onAggregate,
  past7DaysSum,
  past30DaysSum,
}) {
  // Get currency from localStorage, default to CNY
  const currency = (typeof window !== "undefined" && localStorage.getItem("currency")) || "CNY";


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
      label: "Total Sum",
      sum: totalSum,
      gradient: "linear-gradient(135deg, #111827, #1f2937)",
      onClick: () => handleCardClick({ type: "total", start: null, end: null }),
    },
    {
      key: "past7",
      label: "Past 7 Days",
      sum: past7DaysSum,
      gradient: "linear-gradient(135deg, #be185d, #f472b6)",
      onClick: () => handleCardClick({ type: "past7", start: null, end: null, days: 7 }),
    },
    {
      key: "past30",
      label: "Past 30 Days",
      sum: past30DaysSum,
      gradient: "linear-gradient(135deg, #f59e42, #fbbf24)",
      onClick: () => handleCardClick({ type: "past30", start: null, end: null, days: 30 }),
    },
  ];

  // Only add custom card if custom range is set
  if (dateRange[0] && dateRange[1]) {
    cards.push({
      key: "custom",
      label: "Custom Range",
      sum: customSum,
      caption: `${format(dateRange[0], "MMM d")} – ${format(dateRange[1], "MMM d, yyyy")}`,
      gradient: "linear-gradient(135deg, #0ea5e9, #38bdf8)",
      onClick: () => handleCardClick({ type: "custom", start: dateRange[0], end: dateRange[1] }),
    });
  }

  // Sort cards by sum descending
  const sortedCards = [...cards].sort((a, b) => a.sum - b.sum);

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
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}