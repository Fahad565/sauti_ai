// Issues explorer — searchable / filterable table of categorized complaints.

import { api } from "./api.js";
import { getActiveConstituency } from "./app.js";
import { el, clear, pill, loadingCard, fmtTime } from "./ui.js";

const state = {
  constituency: "",
  category: "",
  severity: "",
  topic: "",
  selected: null,
};

let lastData = { items: [], facets: { constituencies: [], categories: [], severities: [] } };

function severityPill(sev) {
  return pill((sev || "medium"), `severity-${(sev || "medium").toLowerCase()}`);
}
function statusPill(s) {
  return pill(s || "open", `status-${(s || "open").toLowerCase().replace(/\s+/g, "_")}`);
}

function buildTable(items) {
  const wrap = el("div", { class: "table-wrap" });
  const table = el("table", { class: "data" });
  table.appendChild(
    el("thead", {}, [
      el("tr", {}, [
        el("th", { text: "Title" }),
        el("th", { text: "Category" }),
        el("th", { text: "Severity" }),
        el("th", { text: "Status" }),
        el("th", { text: "Constituency" }),
        el("th", { text: "Citizen" }),
        el("th", { text: "Created" }),
      ]),
    ])
  );
  const tbody = el("tbody");
  items.forEach((it) => {
    const tr = el("tr", { onclick: () => openDetail(it) }, [
      el("td", { text: it.title || "(untitled)" }),
      el("td", { text: it.category || "—" }),
      el("td", {}, [severityPill(it.severity)]),
      el("td", {}, [statusPill(it.status)]),
      el("td", { text: it.constituency || "—" }),
      el("td", { text: it.citizen_name || it.citizen_phone || "—" }),
      el("td", { text: fmtTime(it.created_at) }),
    ]);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}

function buildFilters(facets) {
  const f = facets || { constituencies: [], categories: [], severities: [] };
  const opts = (arr, currentVal) => [el("option", { value: "", text: "All" })].concat(
    arr.map((x) => el("option", { value: x.value, text: `${x.value} (${x.count})`, selected: x.value === currentVal }))
  );
  const onChange = () => load();
  return el("div", { class: "filter-bar" }, [
    el("label", {}, [
      el("span", { text: "Constituency" }),
      el(
        "select",
        {
          onchange: (e) => {
            state.constituency = e.target.value;
            onChange();
          },
        },
        opts(f.constituencies, state.constituency)
      ),
    ]),
    el("label", {}, [
      el("span", { text: "Category" }),
      el(
        "select",
        {
          onchange: (e) => {
            state.category = e.target.value;
            onChange();
          },
        },
        opts(f.categories, state.category)
      ),
    ]),
    el("label", {}, [
      el("span", { text: "Severity" }),
      el(
        "select",
        {
          onchange: (e) => {
            state.severity = e.target.value;
            onChange();
          },
        },
        opts(f.severities, state.severity)
      ),
    ]),
    el("label", {}, [
      el("span", { text: "Topic contains" }),
      el("input", {
        type: "text",
        placeholder: "e.g. hospital",
        value: state.topic,
        oninput: (e) => {
          state.topic = e.target.value;
        },
      }),
    ]),
    el(
      "button",
      {
        onclick: () => {
          load();
        },
      },
      ["Search"]
    ),
    el(
      "button",
      {
        onclick: () => {
          state.constituency = "";
          state.category = "";
          state.severity = "";
          state.topic = "";
          load();
        },
      },
      ["Reset"]
    ),
  ]);
}

async function load() {
  const page = document.getElementById("page");
  clear(page);
  page.appendChild(loadingCard("Loading issues…"));
  try {
    lastData = await api.issues({
      constituency: state.constituency,
      category: state.category,
      severity: state.severity,
      topic: state.topic,
    });
  } catch (err) {
    clear(page);
    page.appendChild(el("div", { class: "error", text: `Failed to load issues: ${err.message}` }));
    return;
  }
  clear(page);
  page.appendChild(
    el("section", {}, [
      el("div", { class: "section-header" }, [
        el("div", {}, [
          el("h2", { class: "section-title", text: state.constituency ? `Issues Explorer — ${state.constituency}` : "Issues Explorer" }),
          el("p", {
            class: "section-sub",
            text: `${lastData.items.length} issue${lastData.items.length === 1 ? "" : "s"} matching the active filters.`,
          }),
        ]),
      ]),
      buildFilters(lastData.facets),
    ])
  );
  if (lastData.items.length === 0) {
    page.appendChild(el("div", { class: "empty", text: "No issues match the current filters." }));
  } else {
    page.appendChild(buildTable(lastData.items));
  }
}

function openDetail(it) {
  const modal = document.getElementById("modal");
  const close = () => {
    modal.hidden = true;
    modal.innerHTML = "";
  };
  modal.innerHTML = "";
  modal.appendChild(
    el("div", { class: "modal-card" }, [
      el("h2", { text: it.title || "(untitled issue)" }),
      el(
        "p",
        {
          class: "section-sub",
          text: `${it.category || "—"} • ${it.constituency || "—"} • ${fmtTime(it.created_at)}`,
        }
      ),
      el("dl", { class: "kv" }, [
        el("dt", { text: "Severity" }),
        el("dd", {}, [severityPill(it.severity)]),
        el("dt", { text: "Status" }),
        el("dd", {}, [statusPill(it.status)]),
        el("dt", { text: "Citizen" }),
        el("dd", { text: it.citizen_name || it.citizen_phone || "—" }),
        el("dt", { text: "Phone" }),
        el("dd", { text: it.citizen_phone || "—" }),
        el("dt", { text: "Constituency" }),
        el("dd", { text: it.constituency || "—" }),
        el("dt", { text: "Ward" }),
        el("dd", { text: it.ward || "—" }),
        el("dt", { text: "Message" }),
        el("dd", {}, [
          el("p", { text: it.message_full || it.message || "—" }),
        ]),
      ]),
      el(
        "div",
        { style: "margin-top:16px; text-align:right" },
        [el("button", { onclick: close, text: "Close" })]
      ),
    ])
  );
  modal.hidden = false;
  modal.onclick = (ev) => {
    if (ev.target === modal) close();
  };
}

export async function renderIssues(page) {
  state.constituency = getActiveConstituency();
  await load();
}
