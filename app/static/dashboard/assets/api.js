// Lightweight API client for the dashboard SPA.
// Uses fetch against the FastAPI service at the same origin.

const BASE = ""; // same-origin

async function getJson(path) {
  const res = await fetch(BASE + path, { headers: { Accept: "application/json" } });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GET ${path} → ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  overview: (params = {}) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") qs.set(k, v);
    }
    return getJson(`/api/v1/dashboard/overview?${qs.toString()}`);
  },
  issues: (params = {}) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") qs.set(k, v);
    }
    return getJson(`/api/v1/dashboard/issues?${qs.toString()}`);
  },
  infrastructureSummary: (params = {}) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") qs.set(k, v);
    }
    return getJson(`/api/v1/dashboard/infrastructure/summary?${qs.toString()}`);
  },
  infrastructure: (params = {}) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") qs.set(k, v);
    }
    return getJson(`/api/v1/infrastructure?${qs.toString()}`);
  },
  projectsSummary: (params = {}) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") qs.set(k, v);
    }
    return getJson(`/api/v1/dashboard/projects/summary?${qs.toString()}`);
  },
  projects: (params = {}) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") qs.set(k, v);
    }
    return getJson(`/api/v1/projects?${qs.toString()}`);
  },
  activity: (limit = 20, constituency = "") => {
    const qs = new URLSearchParams({ limit: limit.toString() });
    if (constituency) qs.set("constituency", constituency);
    return getJson(`/api/v1/dashboard/activity?${qs.toString()}`);
  },
  pipelinePreview: (message, constituency) => {
    const qs = new URLSearchParams({ message });
    if (constituency) qs.set("constituency", constituency);
    return getJson(`/api/v1/dashboard/pipeline/preview?${qs.toString()}`);
  },
  searchAll: (q, constituency) => {
    const qs = new URLSearchParams({ q });
    if (constituency) qs.set("constituency", constituency);
    qs.set("limit", "5");
    return getJson(`/api/v1/search?${qs.toString()}`);
  },
};
