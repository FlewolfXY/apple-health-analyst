#!/usr/bin/env python3
"""
onboard.py -- One-command setup for an Apple Health analysis workspace.

This wrapper is intentionally boring: it runs inventory.py, runs build_daily.py,
and creates the state files the agent expects. The agent still writes the
human-facing first report, because that part should use the user's interview
answers and the current conversation.

Usage:
    python3 onboard.py /path/to/export.xml --out analysis/
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export_xml")
    ap.add_argument("--out", default="analysis",
                    help="analysis output directory (default: analysis/)")
    ap.add_argument("--events", default=None,
                    help="optional existing events.csv to copy into analysis/")
    args = ap.parse_args()

    export_xml = Path(args.export_xml).expanduser().resolve()
    if not export_xml.exists():
        raise SystemExit(f"export.xml not found: {export_xml}")

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "experiments").mkdir(exist_ok=True)

    script_dir = Path(__file__).resolve().parent
    inventory_json = out / "inventory.json"

    print("== 1/3 Mapping Apple Health export ==")
    run([sys.executable, str(script_dir / "inventory.py"), str(export_xml),
         "--json", str(inventory_json)])

    print("\n== 2/3 Building cleaned daily table ==")
    run([sys.executable, str(script_dir / "build_daily.py"), str(export_xml),
         "--out", str(out)])

    print("\n== 3/3 Initializing analyst state ==")
    init_events(out, args.events)
    init_findings(out)
    init_state(out, export_xml)

    print("\nWorkspace ready.")
    print(f"- daily table: {out / 'daily.csv'}")
    print(f"- metadata:    {out / 'meta.json'}")
    print(f"- state:       {out / 'STATE.md'}")
    print("\nNext: ask the agent to write analysis/first_report.md.")


def run(cmd):
    subprocess.run(cmd, check=True)


def init_events(out, events_path):
    dst = out / "events.csv"
    if dst.exists():
        return
    if events_path:
        src = Path(events_path).expanduser().resolve()
        if not src.exists():
            raise SystemExit(f"events file not found: {src}")
        dst.write_text(src.read_text(), encoding="utf-8")
    else:
        dst.write_text("date,event,category,notes\n", encoding="utf-8")


def init_findings(out):
    path = out / "findings.md"
    if path.exists():
        return
    path.write_text(
        "# Findings Ledger\n\n"
        "Append-only. Every entry should include: verdict, evidence grade, "
        "numbers, caveats, and the query that produced it.\n",
        encoding="utf-8",
    )


def init_state(out, export_xml):
    path = out / "STATE.md"
    meta = load_json(out / "meta.json")
    inventory = load_json(out / "inventory.json")
    coverage = inventory.get("coverage", {})
    rows = meta.get("rows", "?")
    cols = len(meta.get("columns", {}))
    traps = len(meta.get("traps_applied", []))
    notable = len(meta.get("notable_periods", []))
    behavior = len(meta.get("behavior_changes", []))
    generated = datetime.now().isoformat(timespec="seconds")

    text = f"""# Analyst State

- **Export**: `{export_xml}` ({coverage.get('first', '?')} -> {coverage.get('last', '?')})
- **Built**: {generated}
- **Daily table**: `{out / 'daily.csv'}` ({rows} rows x {cols} data columns)
- **Metadata**: `{out / 'meta.json'}` ({traps} traps fixed, {notable} notable periods, {behavior} behavior shifts)
- **First report**: not written yet
- **Open experiments**: none

## Session log

- {generated} · Onboarding wrapper completed. Agent should now interview the user (if not already done), write `first_report.md`, and append first findings to `findings.md`.
"""
    path.write_text(text, encoding="utf-8")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    main()
