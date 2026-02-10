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
import { Fullscreen, FullscreenExit, SwapHoriz, Download } from "@mui/icons-material";
import CloseIcon from "@mui/icons-material/Close";
import ReactECharts from "echarts-for-react";

// Pastel and semi-transparent colors for top-level categories
const CATEGORY_COLORS = [
  "rgba(255, 209, 102, 0.55)", // pastel yellow
  "rgba(6, 214, 160, 0.55)",   // pastel green
  "rgba(239, 71, 111, 0.55)",  // pastel red
  "rgba(17, 138, 178, 0.55)",  // pastel blue
  "rgba(255, 181, 167, 0.55)", // pastel pink
  "rgba(181, 234, 215, 0.55)", // pastel mint
  "rgba(199, 206, 234, 0.55)", // pastel purple
  "rgba(255, 214, 165, 0.55)", // pastel orange
  "rgba(226, 240, 203, 0.55)", // pastel lime
  "rgba(255, 218, 193, 0.55)", // pastel peach
  "rgba(181, 208, 230, 0.55)", // pastel sky
];

const ROOT_COLOR = "rgba(74, 144, 226, 0.55)"; // pastel blue for root

const COLORS = [
  ROOT_COLOR,
  ...CATEGORY_COLORS,
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

  // Get currency from localStorage, default to CNY
  const currency = (typeof window !== "undefined" && localStorage.getItem("currency")) || "CNY";
  let currencySymbol = "元";
  if (currency === "USD") currencySymbol = "$";
  else if (currency === "EUR") currencySymbol = "€";
  else if (currency !== "CNY") currencySymbol = currency;

  const formatValue = React.useCallback(
    (v) => `${new Intl.NumberFormat().format(v)} ${currencySymbol}`,
    [currencySymbol]
  );

  const [fullScreen, setFullScreen] = React.useState(false);

  // Toggle between Sankey and ECharts view
  const [view, setView] = React.useState("sankey");
  const handleToggleView = () => setView((v) => (v === "sankey" ? "echarts" : "sankey"));

  // Transform data for ECharts (sunburst/tree) with pastel coloring (no gradient)
  // Each top-level category gets a pastel color, children inherit the same color
  const echartsData = React.useMemo(() => {
    if (!data || !data.nodes || !data.links) return null;
    if (!data.nodes.length || !data.links.length) return null;

    // Find the root node ("Total Expenses")
    const rootIdx = data.nodes.findIndex((n) => n.name === "Total Expenses");
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

    // Sum up the absolute values of all ignored (negative) nodes (except root)
    const negativeSum = data.nodes
      .map((n, i) => {
        const isChild = data.links.some((l) => l.target === i);
        return i !== rootIdx && n.value < 0 && isChild ? n.value : 0;
      })
      .reduce((acc, v) => acc + v, 0);
    nodeMap[rootIdx].value = -nodeMap[rootIdx].value + -negativeSum;

    // Assign pastel colors: each top-level category gets a color, children inherit it
    function assignColors(node, color = ROOT_COLOR, depth = 0, topLevelIdx = 0) {
      let nodeColor = color;
      if (depth === 0) {
        nodeColor = ROOT_COLOR;
      } else if (depth === 1) {
        nodeColor = CATEGORY_COLORS[topLevelIdx % CATEGORY_COLORS.length];
      }
      // All children of a top-level category inherit its color
      let itemStyle = { color: nodeColor };
      return {
        name: node.name,
        value: node.value,
        itemStyle,
        ...(node.children.length > 0
          ? {
              children: node.children.map((child, i) =>
                assignColors(
                  child,
                  depth === 0
                    ? CATEGORY_COLORS[i % CATEGORY_COLORS.length]
                    : nodeColor,
                  depth + 1,
                  depth === 0 ? i : topLevelIdx
                )
              ),
            }
          : {}),
      };
    }

    return [assignColors(nodeMap[rootIdx])];
  }, [data]);

  // ECharts option
  const echartsOption = React.useMemo(() => {
    if (!echartsData) return {};
    return {
      backgroundColor: "#fafbfc",
      tooltip: {
        trigger: "item",
        backgroundColor: "#222",
        borderColor: "#aaa",
        borderWidth: 1,
        textStyle: { color: "#fff", fontWeight: 500 },
        extraCssText: "box-shadow: 0 2px 12px rgba(0,0,0,0.4);",
        formatter: (info) =>
          `<b>${info.name}</b><br/>${formatValue(info.value)}`,
      },
      series: [
        {
          type: "sunburst",
          data: echartsData,
          radius: ["5%", "99%"],
          sort: null,
          highlightPolicy: "ancestor",
          label: {
            // Use 'rotate: "tangential"' for radial arrangement
            rotate: "tangential",
            color: "#333",
            fontWeight: 600,
            fontSize: 14,
            overflow: "truncate",
            ellipsis: "...",
            minAngle: 8,
            show: true,
            silent: false,
            formatter: (params) =>
              params.data && params.data.name && params.data.name.length > 18
                ? params.data.name.slice(0, 15) + "…"
                : params.data && params.data.name
                  ? params.data.name
                  : "",
          },
          labelLayout: {
            hideOverlap: true,
          },
          itemStyle: {
            borderColor: "#fff",
            borderWidth: 2,
            shadowBlur: 8,
            shadowColor: "rgba(0,0,0,0.08)",
          },
          emphasis: {
            focus: "ancestor",
            itemStyle: {
              shadowBlur: 18,
              shadowColor: "rgba(0,0,0,0.18)",
              borderWidth: 3,
            },
            label: { fontWeight: "bolder", fontSize: 16 },
          },
        },
      ],
    };
  }, [echartsData, formatValue]);

  // Sankey ref for image export
  const sankeyRef = React.useRef(null);
  // ECharts ref for image export
  const echartsRef = React.useRef(null);

  // Download handler (export at fixed size, independent of current display)
  const handleDownloadImage = () => {
    if (view === "sankey" && sankeyData && sankeyData !== "empty") {
      // Render a hidden SVG at fixed size, then export as PNG
      const width = 1920;
      const height = 1080;
      const tempDiv = document.createElement("div");
      tempDiv.style.position = "fixed";
      tempDiv.style.left = "-99999px";
      tempDiv.style.width = `${width}px`;
      tempDiv.style.height = `${height}px`;
      document.body.appendChild(tempDiv);

      // Use createRoot for React 18+
      import("@nivo/sankey").then(({ Sankey }) => {
        const { createRoot } = require("react-dom/client");
        const root = createRoot(tempDiv);
        root.render(
          React.createElement(Sankey, {
            data: sankeyData,
            width,
            height,
            margin: { top: 20, right: 160, bottom: 20, left: 160 },
            align: "justify",
            colors: { scheme: "category10" },
            nodeOpacity: 1,
            nodeHoverOthersOpacity: 0.35,
            nodeThickness: 18,
            nodeSpacing: 24,
            nodeBorderWidth: 0,
            nodeBorderRadius: 3,
            linkOpacity: 0.5,
            linkHoverOthersOpacity: 0.1,
            linkContract: 3,
            enableLinkGradient: true,
            label: (n) => `${n.id} (${formatValue(n.value)})`,
            labelPosition: "outside",
            labelOrientation: "horizontal",
            labelPadding: 16,
            labelTextColor: {
              from: "color",
              modifiers: [["darker", 1]],
            },
            theme: {
              background: "#fff",
            },
            animate: false,
            isInteractive: false,
          })
        );
        setTimeout(() => {
          const svgNode = tempDiv.querySelector("svg");
          if (!svgNode) {
            document.body.removeChild(tempDiv);
            root.unmount();
            return;
          }
          const serializer = new XMLSerializer();
          const svgString = serializer.serializeToString(svgNode);
          const img = new window.Image();
          const svgBlob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
          const url = URL.createObjectURL(svgBlob);
          img.onload = function () {
            const canvas = document.createElement("canvas");
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "#fff";
            ctx.fillRect(0, 0, width, height);
            ctx.drawImage(img, 0, 0, width, height);
            const pngUrl = canvas.toDataURL("image/png");
            const a = document.createElement("a");
            a.href = pngUrl;
            a.download = "sankey.png";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            root.unmount();
            document.body.removeChild(tempDiv);
          };
          img.src = url;
        }, 100); // Give React time to render SVG
      });
    } else if (view === "echarts" && echartsRef.current) {
      // ECharts: use getDataURL with fixed size and high pixel ratio
      const echartsInstance = echartsRef.current.getEchartsInstance();
      // Save original size
      const originalWidth = echartsInstance.getWidth();
      const originalHeight = echartsInstance.getHeight();
      // Temporarily resize for export
      echartsInstance.resize({ width: 1920, height: 1080 });
      setTimeout(() => {
        const url = echartsInstance.getDataURL({
          type: "png",
          pixelRatio: 2,
          backgroundColor: "#fff",
          excludeComponents: ["toolbox"],
        });
        const a = document.createElement("a");
        a.href = url;
        a.download = "sunburst.png";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        // Restore original size
        echartsInstance.resize({ width: originalWidth, height: originalHeight });
      }, 300);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xl" fullScreen={fullScreen}>
      <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span>{title || "Aggregation Results"}</span>
        <Box>
          {/* Only the close button in the top right */}
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
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
          <Box sx={{ width: "100%", height: "100%" }} ref={sankeyRef}>
            <ResponsiveSankey
              data={sankeyData}
              margin={{ top: 20, right: 160, bottom: 20, left: 160 }}
              align="center"
              colors={{ scheme: "category10" }}
              nodeOpacity={1}
              nodeHoverOthersOpacity={0.35}
              nodeThickness={12}
              nodeSpacing={24}
              nodeBorderWidth={0}
              nodeBorderRadius={3}
              linkOpacity={0.5}
              linkHoverOthersOpacity={0.1}
              linkContract={1}
              enableLinkGradient={true}
              label={(n) => `${n.id} (${formatValue(n.value)})`}
              labelPosition="outside"
              labelOrientation="horizontal"
              labelPadding={20}
              labelTextColor={{
                from: "color",
                modifiers: [["darker", 1]],
              }}
            />
          </Box>
        )}

        {!loading && !error && echartsData && view === "echarts" && (
          <Box sx={{ width: "100%", height: "100%", minHeight: 400 }}>
            <ReactECharts
              ref={echartsRef}
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
          onClick={handleDownloadImage}
          variant="outlined"
          color="secondary"
          startIcon={<Download />}
        >
          Download Image
        </Button>
        <Button
          onClick={handleToggleView}
          variant="outlined"
          color="secondary"
          startIcon={<SwapHoriz />}
        >
          Toggle View
        </Button>
        <Button
          onClick={() => setFullScreen((v) => !v)}
          variant="outlined"
          color="secondary"
          startIcon={fullScreen ? <FullscreenExit /> : <Fullscreen />}
        >
          {fullScreen ? "Exit Full Screen" : "Full Screen"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}