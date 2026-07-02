# Agent Instructions

This repository contains an agent-agnostic Apple Health analysis workflow.
Cursor can load it as a Skill through `SKILL.md`; Claude Code can use
`CLAUDE.md`; Codex and other coding agents should follow this file plus
`prompts/apple-health-analyst.md`.

## What To Do

When asked to analyze an Apple Health export:

1. Find `export.xml`.
2. Run the onboarding wrapper:

```bash
python3 /path/to/apple-health-analyst/scripts/onboard.py /path/to/export.xml --out analysis/
```

3. Read `analysis/inventory.json`, `analysis/meta.json`, `analysis/daily.csv`,
   and the relevant playbook under `playbooks/`.
4. Write `analysis/first_report.md`.
5. Append durable conclusions to `analysis/findings.md` and update
   `analysis/STATE.md`.

## Rules

- Do not invent numbers. Query `analysis/daily.csv` or script outputs.
- Do not use user context outside the export and the current conversation.
- Do not commit private health data: `*.xml`, `*.zip`, `analysis/`.
- Use evidence grades for conclusions: strong, moderate, weak.
- For intervention questions, check season, trend, illness, cycle phase, and
  co-occurring life changes.
- If the data cannot answer the question, say so.

## Tests

Run:

```bash
python3 -m unittest discover -s tests
```

The tests use synthetic HealthKit data only.
