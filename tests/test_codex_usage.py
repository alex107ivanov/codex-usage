import unittest
from datetime import datetime

import codex_usage


PAYLOAD = {
    "plan_type": "pro",
    "rate_limit": {
        "primary_window": {
            "used_percent": 42,
            "limit_window_seconds": 604800,
            "reset_at": 1786287600,
        },
        "secondary_window": None,
    },
    "additional_rate_limits": [
        {
            "limit_name": "GPT-5.3-Codex-Spark",
            "rate_limit": {
                "primary_window": {
                    "used_percent": 7,
                    "limit_window_seconds": 604800,
                    "reset_at": 1786287600,
                }
            },
        }
    ],
}


class CodexUsageTests(unittest.TestCase):
    def test_analyze_normalizes_main_and_model_limits(self):
        result = codex_usage.analyze(PAYLOAD, now=datetime(2026, 8, 2, 12, 0))
        self.assertEqual(result["plan_type"], "pro")
        self.assertEqual([item["label"] for item in result["windows"]], ["1-week", "GPT-5.3-Codex-Spark"])
        self.assertEqual(result["windows"][0]["pct"], 42)

    def test_swiftbar_shows_primary_usage_and_model_limit(self):
        result = codex_usage.analyze(PAYLOAD, now=datetime(2026, 8, 2, 12, 0))
        report = codex_usage.swiftbar_report(result)
        self.assertIn("42%", report)
        self.assertIn("GPT-5.3-Codex-Spark: 7% used", report)

    def test_missing_windows_is_actionable(self):
        with self.assertRaisesRegex(codex_usage.UsageError, "did not return"):
            codex_usage.analyze({"rate_limit": {}}, now=datetime(2026, 8, 2, 12, 0))


if __name__ == "__main__":
    unittest.main()
