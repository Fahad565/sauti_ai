// Analytics page — full-bleed charts across all dashboards.

import { api } from "./api.js";
import { getActiveConstituency } from "./app.js";
import {
  el,
  clear,
  barRow,
  donutChart,
  colorAt,
  lineChart,
  loadingCard,
} from "./ui.js";

export async function renderAnalytics(page) {
  clear(page);
  page.appendChild(loadingCard("Loading analytics…"));
  const activeConst = getActiveConstituency();
  let data;
  try {
    data = await api.overview({ constituency: activeConst });
  } catch (err) {
    clear(page);
    page.appendChild(el("div", { class: "error", text: `Failed to load analytics: ${err.message}` }));
    return;
  }
  clear(page);

  // --- Constituencies bar chart ---
  const constData = data.by_constituency || [];
  const maxConst = Math.max(1, ...constData.map((r) => r.count));
  const constBars = el("div", { class: "bars" });
  constData.forEach((r) => {
    const isCurrent = activeConst && r.constituency === activeConst;
    constBars.appendChild(barRow(`${r.constituency}${isCurrent ? " (Active)" : ""}`, r.count, maxConst, isCurrent ? "#0d9488" : colorAt(0)));
  });

  // --- Category donut ---
  const catData = (data.by_category || []).map((r) => ({ label: r.category, value: r.count }));

  // --- Priority donut ---
  const prioData = (data.by_priority || []).map((r) => ({ label: r.severity, value: r.count }));

  // --- Trend line chart ---
  const trendData = data.trend || [];
  const trendChart = lineChart(
    trendData.map((p) => p.count),
    trendData.map((p) => p.week.slice(5))
  );

  page.appendChild(
    el("section", {}, [
      el("div", { class: "section-header" }, [
        el("div", {}, [
          el("h2", { class: "section-title", text: activeConst ? `Analytics — ${activeConst}` : "Analytics — All Constituencies" }),
          el("p", { class: "section-sub", text: "Multi-dimensional analytical view of citizen report trends and breakdowns." }),
        ]),
      ]),
      el("div", { class: "grid cols-2" }, [
        el("div", { class: "card" }, [
          el("p", { class: "card-title", text: "Complaints by constituency" }),
          constBars,
        ]),
        el("div", { class: "card" }, [
          el("p", { class: "card-title", text: `Complaints by category (${activeConst || "All"})` }),
          catData.length > 0
            ? el("div", { class: "donut-wrap" }, [
                donutChart(catData),
                el(
                  "div",
                  { class: "donut-legend" },
                  catData.map((d, i) =>
                    el("div", { class: "donut-legend-row" }, [
                      el("span", { class: "swatch", style: `background:${colorAt(i)}` }),
                      el("span", { text: `${d.label}: ${d.value}` }),
                    ])
                  )
                ),
              ])
            : el("div", { class: "empty", text: "No data yet" }),
        ]),
      ]),
    ])
  );

  page.appendChild(
    el("section", { class: "grid cols-2" }, [
      el("div", { class: "card" }, [
        el("p", { class: "card-title", text: "Priority mix" }),
        prioData.length > 0
          ? el("div", { class: "donut-wrap" }, [
              donutChart(prioData),
              el(
                "div",
                { class: "donut-legend" },
                prioData.map((d, i) =>
                  el("div", { class: "donut-legend-row" }, [
                    el("span", { class: "swatch", style: `background:${colorAt(i + 3)}` }),
                    el("span", { text: `${d.label}: ${d.value}` }),
                  ])
                )
              ),
            ])
          : el("div", { class: "empty", text: "No data yet" }),
      ]),
      el("div", { class: "card" }, [
        el("p", { class: "card-title", text: "Weekly trend" }),
        trendChart,
      ]),
    ])
  );

  page.appendChild(
    el("section", {}, [
      el("div", { class: "card" }, [
        el("p", { class: "card-title", text: `Top topics (${activeConst || "All"})` }),
        el(
          "div",
          { class: "bars" },
          (data.top_topics || []).map((t) =>
            barRow(
              t.topic,
              t.count,
              Math.max(1, ...(data.top_topics || []).map((x) => x.count)),
              colorAt(2)
            )
          )
        ),
      ]),
    ])
  );
}
