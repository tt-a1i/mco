from __future__ import annotations

from typing import Dict, List


_SEVERITY_ORDER = ("critical", "high", "medium", "low")


def _escape_markdown_cell(value: object) -> str:
    text = str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def _finding_location(finding: Dict[str, object]) -> str:
    evidence = finding.get("evidence")
    if not isinstance(evidence, dict):
        return "-"
    file_path = str(evidence.get("file", "")).strip()
    line = evidence.get("line")
    if not file_path:
        return "-"
    if isinstance(line, int) and line > 0:
        return f"{file_path}:{line}"
    return file_path


def format_markdown_pr(payload: Dict[str, object], findings: List[Dict[str, object]]) -> str:
    counts = {level: 0 for level in _SEVERITY_ORDER}
    for finding in findings:
        severity = str(finding.get("severity", "")).lower()
        if severity in counts:
            counts[severity] += 1

    lines: List[str] = [
        "## MCO Review Summary",
        "",
        f"- Decision: **{payload.get('decision', '-')}**",
        f"- Terminal State: `{payload.get('terminal_state', '-')}`",
        f"- Providers: success `{payload.get('provider_success_count', 0)}` / failure `{payload.get('provider_failure_count', 0)}`",
        f"- Findings: `{payload.get('findings_count', 0)}`",
        "",
        "### Severity Breakdown",
        "",
        "| Severity | Count |",
        "|---|---:|",
    ]
    for level in _SEVERITY_ORDER:
        lines.append(f"| `{level}` | {counts[level]} |")

    lines.append("")
    lines.append("### Findings")
    lines.append("")
    if not findings:
        lines.append("_No findings reported._")
        return "\n".join(lines)

    lines.extend(
        [
            "| Severity | Category | Title | Location | Confidence | Recommendation |",
            "|---|---|---|---|---:|---|",
        ]
    )
    ordered_findings = sorted(
        findings,
        key=lambda item: (
            _SEVERITY_ORDER.index(str(item.get("severity", "low")).lower())
            if str(item.get("severity", "low")).lower() in _SEVERITY_ORDER
            else len(_SEVERITY_ORDER),
            _finding_location(item),
            str(item.get("title", "")),
        ),
    )
    for finding in ordered_findings:
        confidence_value = finding.get("confidence")
        if isinstance(confidence_value, (int, float)):
            confidence_text = f"{float(confidence_value):.2f}"
        else:
            confidence_text = "-"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_escape_markdown_cell(str(finding.get('severity', '-')).lower())}`",
                    _escape_markdown_cell(finding.get("category", "-")),
                    _escape_markdown_cell(finding.get("title", "-")),
                    f"`{_escape_markdown_cell(_finding_location(finding))}`",
                    confidence_text,
                    _escape_markdown_cell(finding.get("recommendation", "-")),
                ]
            )
            + " |"
        )
    return "\n".join(lines)

