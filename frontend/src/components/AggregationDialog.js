import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  CircularProgress,
  Box,
  IconButton,
} from "@mui/material";
import { ResponsiveSankey } from "@nivo/sankey";
import { Fullscreen, FullscreenExit } from "@mui/icons-material";

// Color palette for nodes
const COLORS = [
  "#4cafef",
  "#ff7043",
  "#66bb6a",
  "#ab47bc",
  "#ffa726",
  "#26c6da",
  "#d4e157",
  "#ec407a",
];

export default function AggregationDialog({
  open,
  onClose,
  data,
  loading,
  error,
  title,
}) {
  // Transform data for Nivo Sankey
  const sankeyData = React.useMemo(() => {
    if (!data || !data.nodes || !data.links) return null;

    return {
      nodes: data.nodes.map((n, i) => ({
        id: n.name,
        nodeColor: COLORS[i % COLORS.length],
      })),
      links: data.links.map((l) => ({
        source: data.nodes[l.source].name,
        target: data.nodes[l.target].name,
        value: l.value,
      })),
    };
  }, [data]);

  const formatValue = React.useCallback((v) => new Intl.NumberFormat().format(v), []);
  const [fullScreen, setFullScreen] = React.useState(false);

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xl" fullScreen={fullScreen}>
      <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span>{title || "Aggregation Results"}</span>
        <IconButton
          onClick={() => setFullScreen((v) => !v)}
          size="small"
          aria-label={fullScreen ? "Exit Full Screen" : "Full Screen"}
        >
          {fullScreen ? <FullscreenExit /> : <Fullscreen />}
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ height: fullScreen ? "100vh" : "80vh", p: 2 }}>
        {loading && (
          <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
            <CircularProgress />
          </Box>
        )}

        {error && <Typography color="error">{error}</Typography>}

        {!loading && !error && sankeyData && (
          <Box sx={{ width: "100%", height: "100%" }}>
            <ResponsiveSankey
              data={sankeyData}
              margin={{ top: 20, right: 160, bottom: 20, left: 160 }}
              align="justify"
              colors={{ scheme: "category10" }}
              nodeOpacity={1}
              nodeHoverOthersOpacity={0.35}
              nodeThickness={18}
              nodeSpacing={24}
              nodeBorderWidth={0}
              nodeBorderRadius={3}
              linkOpacity={0.5}
              linkHoverOthersOpacity={0.1}
              linkContract={3}
              enableLinkGradient={true}
              label={(n) => `${n.id} (${formatValue(n.value)})`}
              labelPosition="outside"
              labelOrientation="horizontal"
              labelPadding={16}
              labelTextColor={{
                from: "color",
                modifiers: [["darker", 1]],
              }}
            />
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} variant="contained" color="primary">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}