// Overview / landing page.

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

export async function renderOverview(page) {
  clear(page);
  page.appendChild(loadingCard("Loading overview…"));
  const activeConst = getActiveConstituency();
  let data;
  try {
    data = await api.overview({ constituency: activeConst });
  } catch (err) {
    clear(page);
    page.appendChild(el("div", { class: "error", text: `Failed to load overview: ${err.message}` }));
    return;
  }
  clear(page);

  // --- KPI cards -------------------------------------------------------
  const c = data.cards || {};
  const kpis = [
    { label: "Citizen Reports", value: c.citizen_reports, sub: activeConst ? `${activeConst} Constituency` : "All time" },
    { label: "Open Issues", value: c.open_issues, sub: "Status = open" },
    { label: "Projects", value: c.total_projects, sub: activeConst ? `${activeConst} Projects` : "Across all constituencies" },
    { label: "Infrastructure", value: c.total_infrastructure, sub: activeConst ? `${activeConst} Assets` : "Assets indexed" },
    { label: "Critical / High", value: c.critical_issues, sub: "Issues" },
    { label: "Today's Reports", value: c.todays_reports, sub: "Last 24h" },
    { label: "Citizens", value: c.total_citizens, sub: "Unique phone numbers" },
  ];
  page.appendChild(
    el("section", {}, [
      el("div", { class: "section-header" }, [
        el("div", {}, [
          el("h2", { class: "section-title", text: activeConst ? `At a glance — ${activeConst}` : "At a glance — All Constituencies" }),
          el("p", { class: "section-sub", text: activeConst ? `Real-time intelligence and telemetry for ${activeConst} MP office.` : "Live aggregates from the citizen feedback pipeline." }),
        ]),
      ]),
      el(
        "div",
        { class: "grid cols-4" },
        kpis.map((k) =>
          el(
            "div",
            { class: "card" },
            [
              el("p", { class: "card-title", text: k.label }),
              el("p", { class: "card-value", text: k.value != null ? k.value.toString() : "—" }),
              el("p", { class: "card-sub", text: k.sub }),
            ]
          )
        )
      ),
    ])
  );

  // --- Reports by constituency / category ------------------------------
  const byConstBars = el("div", { class: "bars" });
  const constData = data.by_constituency || [];
  const maxConst = Math.max(1, ...constData.map((r) => r.count));
  constData.forEach((r) => {
    const isCurrent = activeConst && r.constituency === activeConst;
    byConstBars.appendChild(barRow(`${r.constituency}${isCurrent ? " (Active)" : ""}`, r.count, maxConst, isCurrent ? "#0d9488" : colorAt(1)));
  });

  const byCatBars = el("div", { class: "bars" });
  const catData = data.by_category || [];
  const maxCat = Math.max(1, ...catData.map((r) => r.count));
  catData.forEach((r, i) => {
    byCatBars.appendChild(barRow(r.category, r.count, maxCat, colorAt(i + 1)));
  });

  const priorityData = (data.by_priority || []).map((r) => ({
    label: r.severity,
    value: r.count,
  }));

  page.appendChild(
    el("section", { class: "grid cols-2" }, [
      el("div", { class: "card" }, [
        el("p", { class: "card-title", text: "Constituency benchmark" }),
        constData.length > 0 ? byConstBars : el("div", { class: "empty", text: "No data yet" }),
      ]),
      el("div", { class: "card" }, [
        el("p", { class: "card-title", text: `Issues by category (${activeConst || "All"})` }),
        catData.length > 0 ? byCatBars : el("div", { class: "empty", text: "No data yet" }),
      ]),
    ])
  );

  // --- Priority donut + trend ----------------------------------------
  const trendData = data.trend || [];
  const trendChart = lineChart(
    trendData.map((p) => p.count),
    trendData.map((p) => p.week.slice(5))
  );

  page.appendChild(
    el("section", { class: "grid cols-2" }, [
      el("div", { class: "card" }, [
        el("p", { class: "card-title", text: "Issue severity mix" }),
        priorityData.length > 0
          ? el("div", { class: "donut-wrap" }, [
              donutChart(priorityData),
              el(
                "div",
                { class: "donut-legend" },
                priorityData.map((p, i) =>
                  el("div", { class: "donut-legend-row" }, [
                    el("span", { class: "swatch", style: `background:${colorAt(i)}` }),
                    el("span", { text: `${p.label}: ${p.value}` }),
                  ])
                )
              ),
            ])
          : el("div", { class: "empty", text: "No data yet" }),
      ]),
      el("div", { class: "card" }, [
        el("p", { class: "card-title", text: "Submission trend (last 8 weeks)" }),
        trendChart,
      ]),
    ])
  );

  // --- Top topics ----------------------------------------------------
  const topicPills = el("div", { class: "bars" });
  (data.top_topics || []).forEach((t) => {
    topicPills.appendChild(barRow(t.topic, t.count, Math.max(...data.top_topics.map((x) => x.count)), colorAt(2)));
  });
  page.appendChild(
    el("section", {}, [
      el("div", { class: "card" }, [
        el("p", { class: "card-title", text: `Top topics (${activeConst || "All Constituencies"})` }),
        (data.top_topics || []).length > 0
          ? topicPills
          : el("div", { class: "empty", text: "Not enough data yet" }),
      ]),
    ])
  );
}
