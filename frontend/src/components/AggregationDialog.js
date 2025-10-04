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
import { Fullscreen, FullscreenExit, SwapHoriz } from "@mui/icons-material";
import ReactECharts from "echarts-for-react";

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
    if (!data.nodes.length || !data.links.length) return "empty";
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

  // Toggle between Sankey and ECharts view
  const [view, setView] = React.useState("sankey");
  const handleToggleView = () => setView((v) => (v === "sankey" ? "echarts" : "sankey"));


    // Transform data for ECharts (sunburst/tree)
    const echartsData = React.useMemo(() => {
      if (!data || !data.nodes || !data.links) return null;
      if (!data.nodes.length || !data.links.length) return null;

      // Find the root node ("Total Sum")
      const rootIdx = data.nodes.findIndex((n) => n.name === "Total Sum");
      if (rootIdx === -1) return null;

      // Filter out nodes with negative values (except root)
      const filteredNodes = data.nodes
        .map((n, i) => ({ ...n, idx: i }))
        .filter((n, i) => i === rootIdx || n.value >= 0);

      // Build a map for quick lookup
      const nodeMap = {};
      filteredNodes.forEach((n) => {
        nodeMap[n.idx] = { name: n.name, value: n.value, children: [] };
      });

      // Build parent-child relationships, only for filtered nodes
      data.links.forEach((l) => {
        if (nodeMap[l.source] && nodeMap[l.target]) {
          nodeMap[l.source].children.push(nodeMap[l.target]);
        }
      });

      console.log(data.nodes);
      // Sum up the absolute values of all ignored (negative) nodes (except root)
      const negativeSum = data.nodes
        .map((n, i) => {
          // Check if node is not root, has negative value, and is a child (has an incoming link)
          const isChild = data.links.some((l) => l.target === i);
          return i !== rootIdx && n.value < 0 && isChild ? n.value : 0;
        })
        .reduce((acc, v) => acc + v, 0);
      // Negate and add to the root node's value
      nodeMap[rootIdx].value = -nodeMap[rootIdx].value + -negativeSum;

      // Deep copy to avoid mutation
      function deepCopy(node) {
        return {
          name: node.name,
          value: node.value,
          ...(node.children.length > 0
            ? { children: node.children.map(deepCopy) }
            : {}),
        };
      }

      return [deepCopy(nodeMap[rootIdx])];
    }, [data]);

  // ECharts option
  const echartsOption = React.useMemo(() => {
    if (!echartsData) return {};
    console.log(echartsData);
    return {
      // tooltip: { trigger: "item", formatter: "{b}: {c}" },
      series: [
        {
          type: "sunburst",
          data: echartsData,
          radius: [0, "90%"],
          label: { rotate: "radial" },
          emphasis: { focus: 'ancestor' }
        },
      ],
    };
  }, [echartsData]);

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

        {!loading && !error && sankeyData === "empty" && (
          <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
            <Typography color="textSecondary" variant="h6">
              No aggregation data to display.
            </Typography>
          </Box>
        )}

        {!loading && !error && sankeyData && sankeyData !== "empty" && view === "sankey" && (
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

        {!loading && !error && echartsData && view === "echarts" && (
          <Box sx={{ width: "100%", height: "100%" }}>
            <ReactECharts
              option={echartsOption}
              style={{ height: "100%", width: "100%" }}
              notMerge={true}
              lazyUpdate={true}
            />
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button
          onClick={handleToggleView}
          variant="outlined"
          color="secondary"
          startIcon={<SwapHoriz />}
        >
          Toggle View
        </Button>
        <Button onClick={onClose} variant="contained" color="primary">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}