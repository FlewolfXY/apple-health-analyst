#!/usr/bin/env python3
"""Regression tests for the stdlib Apple Health pipeline."""

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OnboardPipelineTest(unittest.TestCase):
    def test_onboard_builds_clean_daily_table(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            export = tmp / "export.xml"
            out = tmp / "analysis"
            export.write_text(synthetic_export(), encoding="utf-8")

            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "onboard.py"),
                 str(export), "--out", str(out)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            with open(out / "daily.csv", newline="") as f:
                rows = list(csv.DictReader(f))
            by_date = {r["date"]: r for r in rows}

            # iPhone + Watch both wrote steps; the cleaned value is max single
            # source for the day, not the naive sum.
            self.assertEqual(float(by_date["2026-01-01"]["steps"]), 1800.0)

            # Two overlapping sleep apps: 23:00-07:00 and 23:30-07:30 should
            # union-merge to 8.5 hours, not 16 hours.
            self.assertAlmostEqual(
                float(by_date["2026-01-02"]["sleep_total_h"]), 8.5)

            # HealthKit often stores percentages as fractions.
            self.assertEqual(float(by_date["2026-01-02"]["spo2_pct"]), 98.0)

            with open(out / "meta.json") as f:
                meta = json.load(f)
            self.assertIn("columns", meta)
            self.assertGreater(meta["columns"]["steps"]["coverage_pct"], 0)
            self.assertTrue(any("steps:" in t for t in meta["traps_applied"]))
            self.assertTrue(any("sleep:" in t for t in meta["traps_applied"]))
            self.assertTrue(any("spo2_pct:" in t for t in meta["traps_applied"]))
            self.assertTrue(
                any(b["metric"] == "daylight_min"
                    for b in meta["behavior_changes"]))

            self.assertTrue((out / "STATE.md").exists())
            self.assertTrue((out / "findings.md").exists())
            self.assertTrue((out / "events.csv").exists())
            self.assertTrue((out / "experiments").is_dir())


def synthetic_export():
    records = [
        record("HKQuantityTypeIdentifierStepCount", "2026-01-01 12:00:00 +0800",
               "2026-01-01 12:10:00 +0800", "1000", "count", "iPhone"),
        record("HKQuantityTypeIdentifierStepCount", "2026-01-01 12:00:00 +0800",
               "2026-01-01 12:10:00 +0800", "1800", "count", "Apple Watch"),
        record("HKQuantityTypeIdentifierOxygenSaturation",
               "2026-01-02 03:00:00 +0800",
               "2026-01-02 03:01:00 +0800", "0.98", "%", "Apple Watch"),
        record("HKCategoryTypeIdentifierSleepAnalysis",
               "2026-01-01 23:00:00 +0800",
               "2026-01-02 07:00:00 +0800",
               "HKCategoryValueSleepAnalysisAsleep", "", "Apple Watch"),
        record("HKCategoryTypeIdentifierSleepAnalysis",
               "2026-01-01 23:30:00 +0800",
               "2026-01-02 07:30:00 +0800",
               "HKCategoryValueSleepAnalysisAsleep", "", "Pillow"),
    ]

    # Full-enough monthly daylight data to trigger the behavior-shift detector:
    # low in Jan-Mar, high from Apr onward.
    for month, value in [(1, 10), (2, 10), (3, 10), (4, 100),
                         (5, 100), (6, 100), (7, 100)]:
        for day in range(1, 29):
            d = f"2026-{month:02d}-{day:02d}"
            records.append(record(
                "HKQuantityTypeIdentifierTimeInDaylight",
                f"{d} 09:00:00 +0800",
                f"{d} 09:10:00 +0800",
                str(value), "min", "Apple Watch"))

    body = "\n".join(records)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
  <ExportDate value="2026-08-01 00:00:00 +0800"/>
  <Me HKCharacteristicTypeIdentifierDateOfBirth="1990-01-01" HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexFemale"/>
{body}
</HealthData>
"""


def record(type_, start, end, value, unit, source):
    unit_attr = f' unit="{unit}"' if unit else ""
    return (
        f'  <Record type="{type_}" sourceName="{source}" sourceVersion="1"'
        f'{unit_attr} creationDate="{end}" startDate="{start}"'
        f' endDate="{end}" value="{value}"/>'
    )


if __name__ == "__main__":
    unittest.main()
