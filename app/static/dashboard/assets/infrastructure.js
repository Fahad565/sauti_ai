// Infrastructure Explorer — type cards + search.

import { api } from "./api.js";
import { getActiveConstituency } from "./app.js";
import { el, clear, pill, loadingCard } from "./ui.js";

const state = { search: "", type: "", constituency: "" };
let lastList = [];
let lastSummary = null;

async function load() {
  const page = document.getElementById("page");
  clear(page);
  page.appendChild(loadingCard("Loading infrastructure…"));
  try {
    const [list, summary] = await Promise.all([
      api.infrastructure({ constituency: state.constituency }),
      api.infrastructureSummary({ constituency: state.constituency }),
    ]);
    lastList = list;
    lastSummary = summary;
  } catch (err) {
    clear(page);
    page.appendChild(el("div", { class: "error", text: `Failed to load infrastructure: ${err.message}` }));
    return;
  }
  clear(page);
  render(page);
}

function render(page) {
  // --- Type cards ----------------------------------------------------
  const types = lastSummary?.by_type || [];
  page.appendChild(
    el("section", {}, [
      el("div", { class: "section-header" }, [
        el("div", {}, [
          el("h2", { class: "section-title", text: state.constituency ? `Infrastructure Explorer — ${state.constituency}` : "Infrastructure Explorer" }),
          el("p", { class: "section-sub", text: "All constituency assets indexed for retrieval." }),
        ]),
      ]),
      el(
        "div",
        { class: "grid cols-4" },
        types.map((t) =>
          el(
            "div",
            {
              class: "card",
              style: "cursor:pointer",
              onclick: () => {
                state.type = t.type;
                render(document.getElementById("page"));
              },
            },
            [
              el("p", { class: "card-title", text: t.type }),
              el("p", { class: "card-value", text: t.count.toString() }),
              el("p", { class: "card-sub", text: "Click to filter list below" }),
            ]
          )
        )
      ),
    ])
  );

  // --- Search + list ------------------------------------------------
  page.appendChild(
    el("section", {}, [
      el("div", { class: "card" }, [
        el("div", { class: "filter-bar" }, [
          el("label", {}, [
            el("span", { text: "Type" }),
            el(
              "select",
              {
                onchange: (e) => {
                  state.type = e.target.value;
                  render(document.getElementById("page"));
                },
              },
              [
                el("option", { value: "", text: "All" }),
                ...types.map((t) => el("option", { value: t.type, text: t.type, selected: t.type === state.type })),
              ]
            ),
          ]),
          el("label", {}, [
            el("span", { text: "Search name / location" }),
            el("input", {
              type: "text",
              value: state.search,
              placeholder: "Likoni, Hospital, Market…",
              oninput: (e) => {
                state.search = e.target.value;
              },
            }),
          ]),
          el(
            "button",
            { onclick: () => render(document.getElementById("page")) },
            ["Search"]
          ),
          el(
            "button",
            {
              onclick: () => {
                state.search = "";
                state.type = "";
                render(document.getElementById("page"));
              },
            },
            ["Reset"]
          ),
        ]),
      ]),
    ])
  );

  const filtered = lastList.filter((it) => {
    if (state.type && it.type !== state.type) return false;
    if (state.search) {
      const hay = `${it.name} ${it.location || ""} ${it.constituency}`.toLowerCase();
      if (!hay.includes(state.search.toLowerCase())) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    page.appendChild(el("div", { class: "empty", text: "No infrastructure matches the current filters." }));
    return;
  }
  const wrap = el("div", { class: "table-wrap" });
  const table = el("table", { class: "data" });
  table.appendChild(
    el("thead", {}, [
      el("tr", {}, [
        el("th", { text: "Name" }),
        el("th", { text: "Type" }),
        el("th", { text: "Constituency" }),
        el("th", { text: "Location" }),
        el("th", { text: "Status" }),
        el("th", { text: "Capacity" }),
      ]),
    ])
  );
  const tbody = el("tbody");
  filtered.forEach((it) => {
    tbody.appendChild(
      el("tr", {}, [
        el("td", { text: it.name || "—" }),
        el("td", { text: it.type || "—" }),
        el("td", { text: it.constituency || "—" }),
        el("td", { text: it.location || "—" }),
        el("td", {}, [pill(it.status || "—", `status-${(it.status || "").toLowerCase()}`)]),
        el("td", { text: it.capacity_details || "—" }),
      ])
    );
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  page.appendChild(el("section", {}, [wrap]));
}

export async function renderInfrastructure(page) {
  state.constituency = getActiveConstituency();
  await load();
}
