from __future__ import annotations

import unittest

from runtime.formatters import format_markdown_pr


class FormatterTests(unittest.TestCase):
    def test_markdown_pr_escapes_cells_and_includes_summary(self) -> None:
        payload = {
            "decision": "PASS",
            "terminal_state": "COMPLETED",
            "provider_success_count": 2,
            "provider_failure_count": 0,
            "findings_count": 1,
        }
        findings = [
            {
                "severity": "high",
                "category": "security",
                "title": "Unsafe | shell usage",
                "recommendation": "Use allowlist\nand avoid interpolation",
                "confidence": 0.8,
                "evidence": {"file": "a.py", "line": 10, "snippet": "x"},
            }
        ]
        text = format_markdown_pr(payload, findings)
        self.assertIn("## MCO Review Summary", text)
        self.assertIn("Unsafe \\| shell usage", text)
        self.assertIn("allowlist<br>and avoid interpolation", text)
        self.assertIn("`a.py:10`", text)

    def test_markdown_pr_handles_empty_findings(self) -> None:
        payload = {
            "decision": "PASS",
            "terminal_state": "COMPLETED",
            "provider_success_count": 1,
            "provider_failure_count": 0,
            "findings_count": 0,
        }
        text = format_markdown_pr(payload, [])
        self.assertIn("_No findings reported._", text)


if __name__ == "__main__":
    unittest.main()

