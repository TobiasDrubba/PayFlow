import React from "react";
import { Grid, Card, CardContent, Typography } from "@mui/material";
import { format } from "date-fns";

export default function SummaryCards({ totalSum, monthlySum, customSum, now, dateRange }) {
  return (
    <Grid container spacing={2} sx={{ mb: 3 }}>
      <Grid item xs={12} md={4}>
        <Card
          elevation={0}
          sx={{
            borderRadius: 3,
            p: 0.5,
            background: "linear-gradient(135deg, #111827, #1f2937)",
            color: "white",
          }}
        >
          <CardContent sx={{ p: 2.5 }}>
            <Typography variant="overline" sx={{ opacity: 0.8 }}>
              Total Sum
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 800 }}>
              {totalSum.toFixed(2)}
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.8 }}>All time</Typography>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={4}>
        <Card
          elevation={0}
          sx={{
            borderRadius: 3,
            p: 0.5,
            background: "linear-gradient(135deg, #0f766e, #14b8a6)",
            color: "white",
          }}
        >
          <CardContent sx={{ p: 2.5 }}>
            <Typography variant="overline" sx={{ opacity: 0.9 }}>
              This Month
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 800 }}>
              {monthlySum.toFixed(2)}
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.9 }}>
              {format(now, "MMMM yyyy")}
            </Typography>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={4}>
        <Card
          elevation={0}
          sx={{
            borderRadius: 3,
            p: 0.5,
            background: "linear-gradient(135deg, #3730a3, #6366f1)",
            color: "white",
          }}
        >
          <CardContent sx={{ p: 2.5 }}>
            <Typography variant="overline" sx={{ opacity: 0.9 }}>
              Custom Range
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 800 }}>
              {customSum.toFixed(2)}
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.9 }}>
              {dateRange[0] && dateRange[1]
                ? `${format(dateRange[0], "MMM d")} – ${format(dateRange[1], "MMM d, yyyy")}`
                : "Pick a date range"}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}