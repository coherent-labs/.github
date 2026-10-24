import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pr_body  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

GOOD = """## Why

WREN-123: a sitting that loses its camera keeps recording.

## Change

- `services/live/recorder.go`: the recorder keeps the last good track.

## Proof

- `viva-mono change finish` passed; new test red at base.

## Risk

- A stuck track records black; the QC check flags it. Revert to roll back.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
"""


def replace(body: str, old: str, new: str) -> str:
    assert old in body, old
    return body.replace(old, new)


class Check(unittest.TestCase):
    def test_a_filled_template_passes(self):
        self.assertEqual(pr_body.problems(GOOD), [])

    def test_none_with_a_reason_stands_in_for_a_card(self):
        body = replace(GOOD, "WREN-123: a sitting", "none: housekeeping, a sitting")
        self.assertEqual(pr_body.problems(body), [])

    def test_a_missing_section_fails(self):
        body = replace(GOOD, "## Risk\n\n- A stuck track records black; the QC check flags it. Revert to roll back.\n", "")
        self.assertIn("missing ## Risk", pr_body.problems(body))

    def test_a_renamed_section_fails(self):
        body = replace(GOOD, "## Why", "## Card")
        found = pr_body.problems(body)
        self.assertIn("missing ## Why", found)
        self.assertIn("unexpected ## Card", found)

    def test_sections_out_of_order_fail(self):
        body = replace(replace(GOOD, "## Change", "## TMP"), "## Proof", "## Change")
        body = replace(body, "## TMP", "## Proof")
        self.assertIn("sections out of order: want Why, Change, Proof, Risk", pr_body.problems(body))

    def test_an_empty_section_fails(self):
        body = replace(GOOD, "- `viva-mono change finish` passed; new test red at base.\n", "")
        self.assertIn("## Proof is empty", pr_body.problems(body))

    def test_a_section_holding_only_its_hint_is_empty(self):
        body = replace(
            GOOD,
            "- `viva-mono change finish` passed; new test red at base.",
            "<!-- Verdicts, not logs. -->",
        )
        self.assertIn("## Proof is empty", pr_body.problems(body))

    def test_why_without_a_card_fails(self):
        body = replace(GOOD, "WREN-123: a sitting", "A sitting")
        self.assertIn("## Why names no card: WREN-NNN, or `none:` and a reason", pr_body.problems(body))

    def test_the_template_placeholder_is_not_a_card(self):
        body = replace(GOOD, "WREN-123", "WREN-NNN")
        self.assertIn("## Why names no card: WREN-NNN, or `none:` and a reason", pr_body.problems(body))

    def test_a_long_body_fails(self):
        body = replace(GOOD, "- `services/live/recorder.go`", "- " + "x" * 1500 + " `services/live/recorder.go`")
        self.assertTrue(any(p.startswith("body is ") and p.endswith("over 1500") for p in pr_body.problems(body)))

    def test_the_attribution_and_hints_do_not_count_towards_the_limit(self):
        padding = "<!-- " + "h" * 2000 + " -->\n"
        body = replace(GOOD, "## Change\n", "## Change\n" + padding)
        self.assertEqual(pr_body.problems(body), [])

    def test_a_bot_appended_footer_does_not_count(self):
        footer = (
            "\n<!-- codesmith:footer -->\n---\n<a href=\"https://app.blacksmith.sh\">"
            + "x" * 1500
            + "</a>\n<!-- codesmith:autofix:disabled -->\n<!-- /codesmith:footer -->\n"
        )
        self.assertEqual(pr_body.problems(GOOD + footer), [])

    def test_a_long_proof_fails(self):
        body = replace(GOOD, "new test red at base.", "new test red at base. " + "y" * 400)
        self.assertTrue(any(p.startswith("## Proof is ") and p.endswith("over 400") for p in pr_body.problems(body)))

    def test_a_pasted_log_in_proof_fails(self):
        log = "```\n" + "\n".join(f"line {i}" for i in range(6)) + "\n```\n"
        body = replace(GOOD, "- `viva-mono change finish` passed; new test red at base.\n", log)
        self.assertIn("## Proof pastes a 6-line block: link the log instead", pr_body.problems(body))

    def test_a_short_block_in_proof_passes(self):
        block = "```\nmake check: ok\n```\n"
        body = replace(GOOD, "- `viva-mono change finish` passed; new test red at base.\n", block)
        self.assertEqual(pr_body.problems(body), [])

    def test_the_exempt_label_skips_every_rule(self):
        self.assertTrue(pr_body.exempt(json.dumps([{"name": "pr-body-exempt"}])))
        self.assertFalse(pr_body.exempt(json.dumps([{"name": "bug"}])))
        self.assertFalse(pr_body.exempt(""))


class Template(unittest.TestCase):
    def test_the_template_has_the_checked_sections_and_passes_once_filled(self):
        template = (ROOT / ".github" / "pull_request_template.md").read_text()
        found = pr_body.problems(template)
        self.assertEqual(
            sorted(p for p in found if p.startswith("missing") or p.startswith("unexpected") or "order" in p),
            [],
        )
        self.assertEqual(set(found), {f"## {s} is empty" for s in pr_body.SECTIONS})

    def test_the_template_fits_the_limit_once_its_hints_are_stripped(self):
        template = (ROOT / ".github" / "pull_request_template.md").read_text()
        self.assertLess(len(pr_body.visible(template)), 200)


class Cli(unittest.TestCase):
    def run_cli(self, body, labels="[]"):
        env = {**os.environ, "PR_BODY": body, "PR_LABELS": labels}
        return subprocess.run(
            [sys.executable, str(Path(pr_body.__file__))], env=env, capture_output=True, text=True
        )

    def test_a_good_body_exits_zero(self):
        self.assertEqual(self.run_cli(GOOD).returncode, 0)

    def test_a_bad_body_exits_one_and_names_each_problem(self):
        result = self.run_cli(replace(GOOD, "## Risk", "## Rollback"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing ## Risk", result.stdout)
        self.assertIn("pull_request_template.md", result.stdout)

    def test_an_exempt_bad_body_exits_zero(self):
        result = self.run_cli("nothing", labels=json.dumps([{"name": "pr-body-exempt"}]))
        self.assertEqual(result.returncode, 0)
        self.assertIn("pr-body-exempt", result.stdout)


if __name__ == "__main__":
    unittest.main()
