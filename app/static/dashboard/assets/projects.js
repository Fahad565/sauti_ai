// Projects Explorer — list + status / constituency / budget filters.

import { api } from "./api.js";
import { getActiveConstituency } from "./app.js";
import { el, clear, pill, loadingCard, fmtMoney, fmtTime } from "./ui.js";

const state = { constituency: "", status: "" };
let lastProjects = [];
let lastSummary = null;

function statusPill(s) {
  return pill(s || "—", `status-${(s || "").toLowerCase().replace(/\s+/g, "_")}`);
}

async function load() {
  const page = document.getElementById("page");
  clear(page);
  page.appendChild(loadingCard("Loading projects…"));
  try {
    const [projects, summary] = await Promise.all([
      api.projects(state),
      api.projectsSummary({ constituency: state.constituency }),
    ]);
    lastProjects = projects;
    lastSummary = summary;
  } catch (err) {
    clear(page);
    page.appendChild(el("div", { class: "error", text: `Failed to load projects: ${err.message}` }));
    return;
  }
  clear(page);
  render(page);
}

function buildFilters() {
  const constituencies = (lastSummary?.by_constituency || []).map((c) => c.constituency);
  const statuses = (lastSummary?.by_status || []).map((s) => s.status);
  const opts = (arr, activeVal) => [el("option", { value: "", text: "All" })].concat(
    arr.map((x) => el("option", { value: x, text: x, selected: x === activeVal }))
  );
  return el("div", { class: "filter-bar" }, [
    el("label", {}, [
      el("span", { text: "Constituency" }),
      el(
        "select",
        {
          onchange: (e) => {
            state.constituency = e.target.value;
            load();
          },
        },
        opts(constituencies, state.constituency)
      ),
    ]),
    el("label", {}, [
      el("span", { text: "Status" }),
      el(
        "select",
        {
          onchange: (e) => {
            state.status = e.target.value;
            load();
          },
        },
        opts(statuses, state.status)
      ),
    ]),
  ]);
}

function render(page) {
  const totalBudget = lastSummary?.budget_total || 0;
  const ongoing = (lastSummary?.by_status || []).find((s) => s.status?.toLowerCase() === "ongoing")?.count || 0;
  const planned = (lastSummary?.by_status || []).find((s) => s.status?.toLowerCase() === "planned")?.count || 0;
  const completed = (lastSummary?.by_status || []).find((s) => s.status?.toLowerCase() === "completed")?.count || 0;

  page.appendChild(
    el("section", {}, [
      el("div", { class: "section-header" }, [
        el("div", {}, [
          el("h2", { class: "section-title", text: state.constituency ? `Projects Explorer — ${state.constituency}` : "Projects Explorer" }),
          el("p", { class: "section-sub", text: "Active, planned, and completed constituency development projects." }),
        ]),
      ]),
      el(
        "div",
        { class: "grid cols-4" },
        [
          kpiCard("Ongoing", ongoing),
          kpiCard("Planned", planned),
          kpiCard("Completed", completed),
          kpiCard("Total budget", fmtMoney(totalBudget)),
        ]
      ),
    ])
  );

  page.appendChild(
    el("section", {}, [
      el("div", { class: "card" }, [el("p", { class: "card-title", text: "Filter" }), buildFilters()]),
    ])
  );

  if (lastProjects.length === 0) {
    page.appendChild(el("div", { class: "empty", text: "No projects match the current filters." }));
    return;
  }
  const wrap = el("div", { class: "table-wrap" });
  const table = el("table", { class: "data" });
  table.appendChild(
    el("thead", {}, [
      el("tr", {}, [
        el("th", { text: "Project" }),
        el("th", { text: "Type" }),
        el("th", { text: "Status" }),
        el("th", { text: "Constituency" }),
        el("th", { text: "Budget" }),
        el("th", { text: "Timeline" }),
      ]),
    ])
  );
  const tbody = el("tbody");
  lastProjects.forEach((p) => {
    tbody.appendChild(
      el("tr", {}, [
        el("td", { text: p.name || "—" }),
        el("td", { text: p.type || "—" }),
        el("td", {}, [statusPill(p.status)]),
        el("td", { text: p.constituency || "—" }),
        el("td", { text: fmtMoney(p.budget) }),
        el("td", { text: `${p.start_date || "—"} → ${p.target_completion_date || "—"}` }),
      ])
    );
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  page.appendChild(el("section", {}, [wrap]));
}

function kpiCard(label, value) {
  return el("div", { class: "card" }, [
    el("p", { class: "card-title", text: label }),
    el("p", { class: "card-value", text: String(value ?? "—") }),
  ]);
}

export async function renderProjects(page) {
  state.constituency = getActiveConstituency();
  await load();
}
