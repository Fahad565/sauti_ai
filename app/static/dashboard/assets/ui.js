// Small DOM/chart helpers used across pages (light mode theme).

const SVG_NS = "http://www.w3.org/2000/svg";

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") {
      node.addEventListener(k.slice(2).toLowerCase(), v);
    } else if (v === false || v == null) {
      // skip
    } else {
      node.setAttribute(k, v);
    }
  }
  appendChildren(node, children);
  return node;
}

export function svg(tag, attrs = {}, children = []) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    node.setAttribute(k, v);
  }
  appendChildren(node, children);
  return node;
}

function appendChildren(parent, children) {
  if (children == null || children === false || children === true) return;
  if (Array.isArray(children)) {
    for (const c of children) {
      appendChildren(parent, c);
    }
  } else if (children instanceof Node) {
    parent.appendChild(children);
  } else if (typeof children === "string" || typeof children === "number") {
    parent.appendChild(document.createTextNode(String(children)));
  }
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

export function pill(text, kind = "") {
  const cls = kind ? `pill ${kind}` : "pill";
  return el("span", { class: cls, text: String(text || "") });
}

export function barRow(label, value, max, color) {
  const pct = max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0;
  return el("div", { class: "bar-row" }, [
    el("div", { text: label, title: label }),
    el(
      "div",
      { class: "bar-track" },
      [
        el("div", {
          class: "bar-fill",
          style: `width:${pct}%; ${color ? `background:${color};` : ""}`,
        }),
      ]
    ),
    el("div", { class: "bar-value", text: value.toString() }),
  ]);
}

const PALETTE = [
  "#0d9488",
  "#0284c7",
  "#d97706",
  "#7c3aed",
  "#db2777",
  "#0891b2",
  "#ca8a04",
  "#e11d48",
  "#16a34a",
  "#475569",
];

export function colorAt(i) {
  return PALETTE[i % PALETTE.length];
}

export function donutChart(data) {
  // data: [{label, value}]
  const total = data.reduce((s, d) => s + d.value, 0);
  const radius = 70;
  const stroke = 22;
  const circumference = 2 * Math.PI * radius;
  const root = svg("svg", { class: "donut", viewBox: "0 0 180 180" });
  if (total === 0) {
    root.appendChild(
      svg("circle", {
        cx: 90,
        cy: 90,
        r: radius,
        fill: "none",
        stroke: "#e2e8f0",
        "stroke-width": stroke,
      })
    );
    root.appendChild(
      svg(
        "text",
        { x: 90, y: 95, "text-anchor": "middle", fill: "#64748b", "font-size": 12 },
        ["No data"]
      )
    );
    return root;
  }
  let offset = 0;
  data.forEach((d, i) => {
    const len = (d.value / total) * circumference;
    const circle = svg("circle", {
      cx: 90,
      cy: 90,
      r: radius,
      fill: "none",
      stroke: colorAt(i),
      "stroke-width": stroke,
      "stroke-dasharray": `${len} ${circumference - len}`,
      "stroke-dashoffset": -offset,
      transform: "rotate(-90 90 90)",
      "stroke-linecap": "butt",
    });
    root.appendChild(circle);
    offset += len;
  });
  root.appendChild(
    svg("text", { x: 90, y: 86, "text-anchor": "middle", fill: "#0f172a", "font-size": 22, "font-weight": 700 }, [
      String(total),
    ])
  );
  root.appendChild(
    svg("text", { x: 90, y: 105, "text-anchor": "middle", fill: "#64748b", "font-size": 11 }, [
      "total",
    ])
  );
  return root;
}

export function lineChart(points, labels) {
  // points: array of numbers, labels: array of strings.
  const width = 600;
  const height = 180;
  const padX = 28;
  const padY = 24;
  const max = Math.max(1, ...points);
  const stepX = points.length > 1 ? (width - padX * 2) / (points.length - 1) : 0;
  const root = svg("svg", { class: "trend", viewBox: `0 0 ${width} ${height}`, preserveAspectRatio: "none" });
  // axes
  root.appendChild(
    svg("line", { x1: padX, y1: height - padY, x2: width - padX, y2: height - padY, stroke: "#e2e8f0" })
  );
  root.appendChild(
    svg("line", { x1: padX, y1: padY, x2: padX, y2: height - padY, stroke: "#e2e8f0" })
  );
  // line
  const coords = points.map((v, i) => {
    const x = padX + i * stepX;
    const y = height - padY - (v / max) * (height - padY * 2);
    return [x, y];
  });
  // fill area
  if (coords.length > 1) {
    const areaPath = [
      `M ${coords[0][0]} ${height - padY}`,
      ...coords.map(([x, y]) => `L ${x} ${y}`),
      `L ${coords[coords.length - 1][0]} ${height - padY}`,
      "Z",
    ].join(" ");
    root.appendChild(
      svg("path", { d: areaPath, fill: "rgba(2,132,199,0.08)", stroke: "none" })
    );
  }
  const linePath = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x} ${y}`).join(" ");
  root.appendChild(svg("path", { d: linePath, fill: "none", stroke: "#0284c7", "stroke-width": 2 }));
  // dots
  coords.forEach(([x, y], i) => {
    root.appendChild(svg("circle", { cx: x, cy: y, r: 3, fill: "#0d9488" }));
  });
  // y-axis label
  root.appendChild(
    svg("text", { x: 4, y: padY + 4, fill: "#64748b", "font-size": 10 }, [String(max)])
  );
  // x labels (first, last, middle if many)
  if (labels && labels.length === points.length) {
    const idxs = [0, Math.floor(labels.length / 2), labels.length - 1];
    idxs.forEach((i) => {
      const [x] = coords[i];
      root.appendChild(
        svg(
          "text",
          { x, y: height - 6, "text-anchor": "middle", fill: "#64748b", "font-size": 10 },
          [labels[i]]
        )
      );
    });
  }
  return root;
}

export function fmtMoney(n) {
  if (typeof n !== "number") return String(n ?? "");
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return n.toFixed(0);
}

export function fmtTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    const now = new Date();
    const diff = (now - d) / 1000;
    if (diff >= 0 && diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff >= 0 && diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff >= 0 && diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return String(iso);
  }
}

export function setStatus(node, ok, text) {
  if (!node) return;
  node.classList.remove("ok", "bad");
  if (ok === true) node.classList.add("ok");
  if (ok === false) node.classList.add("bad");
  if (text != null) {
    const t = document.getElementById("status-text");
    if (t) t.textContent = text;
  }
}

export function loadingCard(label = "Loading…") {
  return el("div", { class: "card" }, [el("div", {}, [el("span", { class: "spinner" }), label])]);
}
