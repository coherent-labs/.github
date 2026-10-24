#!/usr/bin/env python3
"""Fail a PR body that is not the org template, filled in briefly.

    ## Why      WREN-NNN (or `none:` and a reason): the problem in one line
    ## Change   what a reviewer will see in the diff
    ## Proof    verdicts, not logs
    ## Risk     what could break, how we'd notice, how to roll back

HTML comments (the template's hints), the Claude Code attribution line and a bot's footer
(`<!-- codesmith:footer -->` ... `<!-- /codesmith:footer -->`, which Blacksmith appends) do
not count.
The `pr-body-exempt` label, which only a person applies, skips every rule. Standard library only.

    PR_BODY=... PR_LABELS='[{"name": ...}]' pr_body.py
"""

from __future__ import annotations

import json
import os
import re
import sys

SECTIONS = ("Why", "Change", "Proof", "Risk")
MAX_BODY = 1500
MAX_PROOF = 400
MAX_BLOCK_LINES = 5
EXEMPT = "pr-body-exempt"
TEMPLATE = "https://github.com/coherent-labs/.github/blob/main/.github/pull_request_template.md"

FOOTER = re.compile(r"<!-- (\w+):footer -->.*?<!-- /\1:footer -->", re.S)
COMMENT = re.compile(r"<!--.*?-->", re.S)
ATTRIBUTION = re.compile(r"^.*Generated with \[Claude Code\].*$", re.M)
HEADING = re.compile(r"^## +(.+?)\s*$", re.M)
CARD = re.compile(r"\bWREN-\d+\b|^\s*none:\s*\S", re.I | re.M)
FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.S | re.M)


def visible(body: str) -> str:
    text = FOOTER.sub("", body.replace("\r\n", "\n"))
    return ATTRIBUTION.sub("", COMMENT.sub("", text)).strip()


def sections(text: str) -> list[tuple[str, str]]:
    marks = list(HEADING.finditer(text))
    return [
        (m[1], text[m.end() : marks[i + 1].start() if i + 1 < len(marks) else len(text)].strip())
        for i, m in enumerate(marks)
    ]


def problems(body: str) -> list[str]:
    text = visible(body)
    found = sections(text)
    names = [name for name, _ in found]
    content = dict(found)
    out = [f"missing ## {s}" for s in SECTIONS if s not in content]
    out += [f"unexpected ## {n}" for n in names if n not in SECTIONS]
    if [n for n in names if n in SECTIONS] != [s for s in SECTIONS if s in content]:
        out.append(f"sections out of order: want {', '.join(SECTIONS)}")
    out += [f"## {s} is empty" for s in SECTIONS if s in content and not content[s]]
    why = content.get("Why", "")
    if why and not CARD.search(why):
        out.append("## Why names no card: WREN-NNN, or `none:` and a reason")
    if len(text) > MAX_BODY:
        out.append(f"body is {len(text)} characters, over {MAX_BODY}")
    proof = content.get("Proof", "")
    if len(proof) > MAX_PROOF:
        out.append(f"## Proof is {len(proof)} characters, over {MAX_PROOF}")
    for block in FENCE.findall(proof):
        lines = len(block.rstrip("\n").split("\n"))
        if lines > MAX_BLOCK_LINES:
            out.append(f"## Proof pastes a {lines}-line block: link the log instead")
    return out


def exempt(labels_json: str) -> bool:
    try:
        labels = json.loads(labels_json or "[]")
    except json.JSONDecodeError:
        return False
    return any(label.get("name") == EXEMPT for label in labels)


def main() -> int:
    if exempt(os.environ.get("PR_LABELS", "")):
        print(f"pr-body: skipped, the PR carries {EXEMPT}")
        return 0
    found = problems(os.environ.get("PR_BODY") or sys.stdin.read())
    if not found:
        print("pr-body: ok")
        return 0
    print("pr-body: the PR body does not follow the template")
    for p in found:
        print(f"  - {p}")
    print(f"Fill {TEMPLATE} (gh pr edit --body-file). Bullets, verdicts, no logs.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
