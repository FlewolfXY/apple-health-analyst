# Claude Code Instructions

This repository can be used directly from Claude Code, not only as a Cursor
Skill.

When the user asks to analyze an Apple Health export, follow
`prompts/apple-health-analyst.md`.

## Quick Start

From a folder containing `export.xml`, run:

```bash
python3 /path/to/apple-health-analyst/scripts/onboard.py export.xml --out analysis/
```

If this repository itself is the current working directory and the export is
elsewhere, use the export's absolute path:

```bash
python3 scripts/onboard.py /path/to/export.xml --out /path/to/export-folder/analysis/
```

Then read:

- `analysis/inventory.json`
- `analysis/meta.json`
- `analysis/STATE.md`
- `analysis/daily.csv`
- the relevant playbook in `playbooks/`

Write `analysis/first_report.md` and update `analysis/findings.md` /
`analysis/STATE.md`.

## Non-Negotiables

- Keep raw health exports local. Do not upload `export.xml`.
- Never commit `*.xml`, `*.zip`, or `analysis/`.
- Every number in a report or answer must be recomputed from local files in
  the current session.
- Before/after claims must follow `playbooks/intervention.md`.
- If Apple Health cannot answer a question, say so.
