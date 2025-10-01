import React from "react";
import { Grid, Card, CardContent, Typography } from "@mui/material";
import { format } from "date-fns";

// Format sum as negative, integer, add 元, and use K notation if >= 10000
function formatSum(sum) {
  const abs = Math.abs(Math.round(sum));
  let display;
  if (abs >= 10000) {
    display = `${(abs / 1000).toFixed(1)}K 元`;
  } else {
    display = `${abs} 元`;
  }
  return `${display}`;
}

export default function SummaryCards({
  totalSum,
  customSum,
  now,
  dateRange,
  onCardClick,
  past7DaysSum,
  past30DaysSum,
}) {
  // Calculate date ranges for cards
  const past7Start = new Date(now.getTime() - 6 * 24 * 60 * 60 * 1000);
  const past7End = now;
  const past30Start = new Date(now.getTime() - 29 * 24 * 60 * 60 * 1000);
  const past30End = now;

  // Compose all cards with their sums and render info
  const cards = [
    {
      key: "total",
      label: "Total Sum",
      sum: totalSum,
      caption: "All time",
      gradient: "linear-gradient(135deg, #111827, #1f2937)",
      onClick: () => onCardClick && onCardClick({ type: "total", start: null, end: null }),
    },
    {
      key: "past7",
      label: "Past 7 Days",
      sum: past7DaysSum,
      caption: `${format(past7End, "MMM d")} – ${format(past7Start, "MMM d, yyyy")}`,
      gradient: "linear-gradient(135deg, #be185d, #f472b6)",
      onClick: () => onCardClick && onCardClick({ type: "past7", start: past7Start, end: past7End }),
    },
    {
      key: "past30",
      label: "Past 30 Days",
      sum: past30DaysSum,
      caption: `${format(past30End, "MMM d")} – ${format(past30Start, "MMM d, yyyy")}`,
      gradient: "linear-gradient(135deg, #f59e42, #fbbf24)",
      onClick: () => onCardClick && onCardClick({ type: "past30", start: past30Start, end: past30End }),
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
      onClick: () => onCardClick && onCardClick({ type: "custom", start: dateRange[0], end: dateRange[1] }),
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
              cursor: "pointer"
            }}
            onClick={card.onClick}
          >
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="overline" sx={{ opacity: 0.9 }}>
                {card.label}
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 800 }}>
                {formatSum(card.sum)}
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