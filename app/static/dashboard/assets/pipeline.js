// AI Pipeline Visualizer — shows the stages a citizen message flows through
// (intake → classify → retrieval → context → LLM) and lets the user run a
// live preview to see the exact intermediate state.

import { api } from "./api.js";
import { el, clear, pill, loadingCard, fmtTime } from "./ui.js";

const SAMPLE_PROMPTS = [
  "Is there a hospital in Likoni?",
  "Broken bridge in Likoni",
  "The road towards Nyali from Buxton is very poor with potholes",
  "What projects are planned for Mvita?",
  "When will the water project in Jomvu be completed?",
];

const state = {
  message: SAMPLE_PROMPTS[0],
  constituency: "",
  result: null,
};

function stageCard(idx, stage) {
  const head = el(
    "div",
    { class: "stage-head" },
    [
      el("div", { style: "display:flex; align-items:center; gap:8px" }, [
        el("span", { class: "stage-num", text: idx.toString() }),
        el("span", { class: "stage-name", text: stage.label }),
      ]),
      el("span", { class: "stage-meta", text: describe(stage) }),
    ]
  );

  const body = el("div", { class: "stage-body" }, renderBody(stage));

  return el("div", { class: "stage" }, [head, body]);
}

function describe(stage) {
  switch (stage.stage) {
    case "intake":
      return "Captures the inbound message and records its length.";
    case "classify":
      return "Determines intent and constituency. Feeds into retrieval.";
    case "retrieval":
      return "SQL-backed keyword + constituency filter over infrastructure, projects, submissions, and issues.";
    case "context":
      return "Assembles structured Markdown context the LLM will see.";
    case "analyze":
      return "Gemma 4 produces the final civic-grounded answer.";
    default:
      return "";
  }
}

function renderBody(stage) {
  const out = stage.output || {};
  switch (stage.stage) {
    case "intake":
      return [el("p", { text: `Captured ${out.length} character(s) of citizen input.` })];
    case "classify": {
      const conf = Math.round((out.confidence || 0) * 100);
      const kws = (out.keywords_matched || []).join(", ") || "—";
      return [
        el("div", {}, [
          pill(out.intent || "general_question", "intent"),
          el("span", { text: `  confidence: ${conf}%` }),
        ]),
        el("div", { class: "confidence-bar" }, [el("span", { style: `width:${conf}%` })]),
        el("div", { text: `Keywords matched: ${kws}` }),
        el("div", { text: `Constituency detected: ${stage.detected_constituency || "General"}` }),
      ];
    }
    case "retrieval": {
      const r = out;
      return [
        el("div", { text: `Total matches: ${r.total_matches || 0}` }),
        el(
          "div",
          { style: "display:flex; gap:8px; flex-wrap:wrap" },
          [
            pill(`infrastructure: ${r.infrastructure_count || 0}`),
            pill(`projects: ${r.projects_count || 0}`),
            pill(`submissions: ${r.submissions_count || 0}`),
            pill(`issues: ${r.issues_count || 0}`),
          ]
        ),
        el("pre", { text: JSON.stringify(r.top_results || [], null, 2) }),
      ];
    }
    case "context":
      return [
        el("div", { text: `Context size: ${out.context_chars} character(s) (truncated at 4000).` }),
        el("pre", { text: out.preview || "" }),
      ];
    case "analyze":
      return [
        el("div", { text: `System + RAG prompt size: ~${(stage.input.rag_prompt_chars || 0)} character(s).` }),
        el("div", { class: "section-sub", text: stage.output || "(not invoked in dashboard preview)" }),
      ];
    default:
      return [];
  }
}

async function run() {
  const page = document.getElementById("page");
  const target = page.querySelector("#pipeline-output");
  if (!target) return;
  target.innerHTML = "";
  target.appendChild(loadingCard("Running pipeline preview…"));
  try {
    state.result = await api.pipelinePreview(state.message, state.constituency);
  } catch (err) {
    target.innerHTML = "";
    target.appendChild(el("div", { class: "error", text: `Pipeline preview failed: ${err.message}` }));
    return;
  }
  target.innerHTML = "";
  const stages = state.result.stages || [];
  target.appendChild(
    el("div", { class: "pipeline" }, stages.map((s, i) => stageCard(i + 1, s)))
  );
}

function render(page) {
  clear(page);
  page.appendChild(
    el("section", {}, [
      el("div", { class: "section-header" }, [
        el("div", {}, [
          el("h2", { class: "section-title", text: "AI Pipeline Visualizer" }),
          el("p", {
            class: "section-sub",
            text: "Walk through every stage the LangGraph reasoning graph runs for a citizen message — classification, retrieval, context assembly, and the LLM call.",
          }),
        ]),
      ]),
      el("div", { class: "card" }, [
        el("div", { class: "filter-bar" }, [
          el("label", {}, [
            el("span", { text: "Try a prompt" }),
            el(
              "select",
              {
                onchange: (e) => {
                  state.message = e.target.value;
                },
              },
              SAMPLE_PROMPTS.map((s) => el("option", { value: s, text: s }))
            ),
          ]),
          el("label", {}, [
            el("span", { text: "Or write your own" }),
            el("input", {
              type: "text",
              value: state.message,
              oninput: (e) => {
                state.message = e.target.value;
              },
            }),
          ]),
          el("label", {}, [
            el("span", { text: "Force constituency" }),
            el("input", {
              type: "text",
              placeholder: "auto",
              oninput: (e) => {
                state.constituency = e.target.value;
              },
            }),
          ]),
          el("button", { onclick: run, text: "Run pipeline" }),
        ]),
        el("div", { id: "pipeline-output", style: "margin-top:16px" }, []),
      ]),
    ])
  );
  // Auto-run the initial sample so the user sees something on first visit.
  run();
}

export async function renderPipeline(page) {
  render(page);
}
