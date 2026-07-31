// Top-level SPA shell: hash router, status indicator, page dispatcher, constituency context.

import { api } from "./api.js";
import { clear, el } from "./ui.js";

import { renderOverview } from "./overview.js";
import { renderIssues } from "./issues.js";
import { renderProjects } from "./projects.js";
import { renderInfrastructure } from "./infrastructure.js";
import { renderPipeline } from "./pipeline.js";
import { renderActivity } from "./activity.js";

const ROUTES = {
  overview: { title: "Overview", render: renderOverview },
  issues: { title: "Issues", render: renderIssues },
  projects: { title: "Projects", render: renderProjects },
  infrastructure: { title: "Infrastructure", render: renderInfrastructure },
  pipeline: { title: "AI Pipeline", render: renderPipeline },
  activity: { title: "Live Feed", render: renderActivity },
};

const DEFAULT_ROUTE = "overview";

export function getActiveConstituency() {
  const val = localStorage.getItem("sauti_constituency");
  return val !== null ? val : "Likoni";
}

export function setActiveConstituency(c) {
  if (c != null) {
    localStorage.setItem("sauti_constituency", c);
  } else {
    localStorage.removeItem("sauti_constituency");
  }
}

function currentRoute() {
  const hash = window.location.hash.replace(/^#\/?/, "");
  return ROUTES[hash] ? hash : DEFAULT_ROUTE;
}

function setActive(route) {
  document.querySelectorAll(".nav-item").forEach((n) => {
    n.classList.toggle("active", n.dataset.route === route);
  });
  document.getElementById("page-title").textContent = ROUTES[route].title;
}

function setLastUpdated() {
  const el = document.getElementById("last-updated");
  if (el) {
    el.textContent = `Updated ${new Date().toLocaleTimeString()}`;
  }
}

function setStatus(ok, text) {
  const dot = document.getElementById("status-dot");
  if (dot) {
    dot.classList.toggle("ok", ok === true);
    dot.classList.toggle("bad", ok === false);
  }
  if (text) {
    const st = document.getElementById("status-text");
    if (st) st.textContent = text;
  }
}

async function pingBackend() {
  try {
    const constituency = getActiveConstituency();
    const data = await api.overview({ constituency });
    const count = data.cards ? data.cards.citizen_reports || 0 : 0;
    const label = constituency ? `${constituency}: ${count} reports` : `${count} reports total`;
    setStatus(true, `Live • ${label}`);
  } catch (err) {
    setStatus(false, "Backend unreachable");
    console.warn("Backend ping failed", err);
  }
}

async function renderRoute() {
  const route = currentRoute();
  setActive(route);
  const page = document.getElementById("page");
  clear(page);
  try {
    await ROUTES[route].render(page);
    setLastUpdated();
  } catch (err) {
    console.error("[sauti] page render error", err);
    try {
      clear(page);
      const errNode = document.createElement("div");
      errNode.className = "error";
      errNode.textContent = `Page error: ${err.message}`;
      page.appendChild(errNode);
    } catch (_) {
      // suppress secondary DOM errors to keep the shell alive
    }
  }
  // Close mobile sidebar after navigation
  const sb = document.getElementById("sidebar");
  if (sb) sb.classList.remove("open");
}

function setupNav() {
  document.querySelectorAll(".nav-item").forEach((n) => {
    n.addEventListener("click", () => {
      const sb = document.getElementById("sidebar");
      if (sb) sb.classList.remove("open");
    });
  });
}

function setupSidebarToggle() {
  const btn = document.getElementById("hamburger");
  if (btn) {
    btn.addEventListener("click", () => {
      const sb = document.getElementById("sidebar");
      if (sb) sb.classList.toggle("open");
    });
  }
}

function setupConstituencySelector() {
  const select = document.getElementById("constituency-select");
  if (!select) return;
  select.value = getActiveConstituency();
  select.addEventListener("change", (e) => {
    setActiveConstituency(e.target.value);
    renderRoute();
    pingBackend();
  });
}

window.addEventListener("hashchange", renderRoute);
window.addEventListener("DOMContentLoaded", () => {
  if (!window.location.hash) {
    window.location.hash = `#/${DEFAULT_ROUTE}`;
  }
  setupNav();
  setupSidebarToggle();
  setupConstituencySelector();
  renderRoute();
  pingBackend();
  // Refresh status + last-updated every 30s.
  setInterval(() => {
    pingBackend();
    setLastUpdated();
  }, 30000);
});
