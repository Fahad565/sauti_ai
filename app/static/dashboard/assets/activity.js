// Live activity feed — most recent submissions, issues, agent actions, AI summaries.

import { api } from "./api.js";
import { getActiveConstituency } from "./app.js";
import { el, clear, loadingCard, fmtTime } from "./ui.js";

const state = { limit: 30 };

function row(entry) {
  return el("div", { class: "feed-item" }, [
    el("div", { class: "feed-time", text: fmtTime(entry.timestamp) }),
    el("div", { class: "feed-summary" }, [
      el("span", { class: "feed-kind", text: entry.kind.replace("_", " ") }),
      entry.constituency
        ? el("span", { class: "pill", text: entry.constituency, style: "margin-right:6px" })
        : null,
      entry.intent
        ? el("span", { class: "pill intent", text: entry.intent, style: "margin-right:6px" })
        : null,
      el("span", { text: entry.summary || "(no summary)" }),
    ]),
  ]);
}

async function load() {
  const page = document.getElementById("page");
  clear(page);
  page.appendChild(loadingCard("Loading activity…"));
  const activeConst = getActiveConstituency();
  let data;
  try {
    data = await api.activity(state.limit, activeConst);
  } catch (err) {
    clear(page);
    page.appendChild(el("div", { class: "error", text: `Failed to load activity: ${err.message}` }));
    return;
  }
  clear(page);
  page.appendChild(
    el("section", {}, [
      el("div", { class: "section-header" }, [
        el("div", {}, [
          el("h2", { class: "section-title", text: activeConst ? `Live Activity — ${activeConst}` : "Live Activity — All" }),
          el("p", { class: "section-sub", text: "Citizen submissions, issues raised, agent actions, and AI summaries — most recent first." }),
        ]),
        el("div", {}, [
          el(
            "button",
            {
              onclick: () => {
                load();
              },
              text: "Refresh",
            }
          ),
        ]),
      ]),
    ])
  );
  if (!data.items || data.items.length === 0) {
    page.appendChild(el("div", { class: "empty", text: "No activity yet." }));
    return;
  }
  page.appendChild(
    el("section", {}, [el("div", { class: "feed" }, data.items.map(row))])
  );
}

export async function renderActivity(page) {
  await load();
}
