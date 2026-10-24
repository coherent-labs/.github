# coherent-labs/.github

Organisation defaults.

- `.github/pull_request_template.md`: the PR template for every repo that has none of its own.
  Four sections: Why, Change, Proof, Risk.
- `scripts/pr_body.py`: the check that a PR body is that template, filled briefly. Each repo's
  `pr-title` job fetches it from `main` and runs it; the label `pr-body-exempt`, applied by a
  person, skips it. Tests: `python3 -m unittest scripts/test_pr_body.py`.

A change to the checker applies to every repo on merge: run the tests first.
