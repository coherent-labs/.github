## Card

WREN-NNN: what changes and why, in one line.

## Change

- Single PR, or part of a change: <sibling PRs>. Merge order: <e.g. migration → API → FE>

## Route and tier

- Kind: copy | bug | ui | feature | performance | prompt | hotfix | investigate  (`viva change route`)
- Tier: critical | standard | negligible, because …  (`viva flows affected`)
- Person paths: none | infra · auth · migrations · viva-live: …

## Proof

<!-- Run by the harness, not described. Paste the verdict. -->

- Gate: `viva change gate`, new tests red at base and green here: …
- E2E: viva-test scenario and verdict (if a person would see the change): …
- Screens: before and after (UI only)

## Infra (only if Terraform changes)

- Plan in plain English: adds … / changes … / **destroys …**
- terraform-skill Response Contract: <link>

## Risk

- What could break, and how we'd notice. How to roll back.
