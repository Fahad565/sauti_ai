"""Context Builder service for Sauti AI RAG pipeline.

Formats structured retrieval data into clean, readable prompt context strings
with token limits and truncation controls.
"""

from __future__ import annotations

from typing import Any, Dict, List


class ContextBuilder:
    """Formats and builds bounded Markdown context strings from retrieval results."""

    def __init__(self, max_chars: int = 4000):
        self.max_chars = max_chars

    def build_context(self, retrieval_results: Dict[str, Any]) -> str:
        """Format retrieval results into structured prompt context."""
        sections = []

        # Infrastructure
        infra = retrieval_results.get("infrastructure", [])
        if infra:
            infra_lines = ["### Verified Infrastructure Assets"]
            for item in infra:
                name = item.get("name", "N/A")
                itype = item.get("type", "N/A")
                loc = item.get("location", "N/A")
                status = item.get("status", "N/A")
                const = item.get("constituency", "N/A")
                details = item.get("capacity_details")
                detail_str = f" - Details: {details}" if details else ""
                infra_lines.append(
                    f"- **{name}** ({itype}) in {loc}, {const} | Status: {status}{detail_str}"
                )
            sections.append("\n".join(infra_lines))

        # Projects
        projects = retrieval_results.get("projects", [])
        if projects:
            proj_lines = ["### Constituency Projects"]
            for p in projects:
                name = p.get("name", "N/A")
                ptype = p.get("type", "N/A")
                status = p.get("status", "N/A")
                budget = p.get("budget", 0.0)
                desc = p.get("description")
                desc_str = f" - Summary: {desc}" if desc else ""
                target = p.get("target_completion_date")
                target_str = f" (Target Completion: {target})" if target else ""
                proj_lines.append(
                    f"- **{name}** ({ptype}) | Status: {status}{target_str} | Budget: KES {budget:,.2f}{desc_str}"
                )
            sections.append("\n".join(proj_lines))

        # Previous Submissions / Reports
        submissions = retrieval_results.get("submissions", [])
        if submissions:
            sub_lines = ["### Previous Citizen Reports & Submissions"]
            for s in submissions:
                content = s.get("raw_content", "")
                ward = s.get("ward", "N/A")
                status = s.get("status", "N/A")
                sub_lines.append(f"- Report (Ward: {ward}, Status: {status}): \"{content}\"")
            sections.append("\n".join(sub_lines))

        # Issues
        issues = retrieval_results.get("issues", [])
        if issues:
            issue_lines = ["### Known Categorized Issues"]
            for i in issues:
                title = i.get("title", "N/A")
                cat = i.get("category", "N/A")
                sev = i.get("severity", "N/A")
                status = i.get("status", "N/A")
                issue_lines.append(f"- Issue: **{title}** [{cat}] | Severity: {sev} | Status: {status}")
            sections.append("\n".join(issue_lines))

        if not sections:
            return "No matching records found in constituency database."

        combined = "\n\n".join(sections)
        if len(combined) > self.max_chars:
            combined = combined[: self.max_chars - 30] + "\n... [Context truncated]"

        return combined
