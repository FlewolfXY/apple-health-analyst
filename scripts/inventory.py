#!/usr/bin/env python3
"""
inventory.py -- Map an Apple Health export.

Answers three questions in one streaming pass (constant memory, stdlib only):
  1. What data exists, how much, over what span, from which sources?
  2. Which analyses does it unlock (the "skill tree")?
  3. Which known data traps are present (multi-source double counting, etc.)?

Usage:
    python3 inventory.py /path/to/export.xml [--json analysis/inventory.json]
"""

import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

PREFIXES = (
    "HKQuantityTypeIdentifier",
    "HKCategoryTypeIdentifier",
    "HKCharacteristicTypeIdentifier",
    "HKDataType",
)


def short(t):
    for p in PREFIXES:
        if t.startswith(p):
            return t[len(p):]
    return t


# (key, label, member types, (low, high) record-count thresholds for stars)
DOMAINS = [
    ("cardio", "Cardiovascular & Recovery",
     ["HeartRate", "RestingHeartRate", "HeartRateVariabilitySDNN", "VO2Max",
      "WalkingHeartRateAverage", "HeartRateRecoveryOneMinute",
      "OxygenSaturation", "RespiratoryRate"], (1000, 50000)),
    ("sleep", "Sleep",
     ["SleepAnalysis", "AppleSleepingWristTemperature", "SleepDurationGoal"],
     (500, 10000)),
    ("activity", "Activity & Energy",
     ["StepCount", "DistanceWalkingRunning", "DistanceCycling",
      "FlightsClimbed", "ActiveEnergyBurned", "BasalEnergyBurned",
      "AppleExerciseTime", "AppleStandTime", "AppleStandHour",
      "PhysicalEffort"], (5000, 100000)),
    ("gait", "Gait & Mobility (strength proxies)",
     ["WalkingSpeed", "WalkingStepLength", "WalkingDoubleSupportPercentage",
      "WalkingAsymmetryPercentage", "AppleWalkingSteadiness",
      "StairAscentSpeed", "StairDescentSpeed", "SixMinuteWalkTestDistance"],
     (500, 10000)),
    ("running", "Running Biomechanics",
     ["RunningSpeed", "RunningPower", "RunningVerticalOscillation",
      "RunningGroundContactTime", "RunningStrideLength"], (200, 2000)),
    ("hearing", "Hearing Exposure",
     ["HeadphoneAudioExposure", "EnvironmentalAudioExposure",
      "EnvironmentalSoundReduction", "AudioExposureEvent"], (1000, 20000)),
    ("cycle", "Menstrual Cycle",
     ["MenstrualFlow", "IntermenstrualBleeding", "OvulationTestResult",
      "BasalBodyTemperature", "CervicalMucusQuality"], (24, 100)),
    ("behavior", "Light, Mindfulness & Habits",
     ["TimeInDaylight", "MindfulSession", "HandwashingEvent",
      "ToothbrushingEvent"], (100, 1000)),
    ("body", "Body Measurements",
     ["BodyMass", "Height", "BodyMassIndex", "BodyFatPercentage",
      "LeanBodyMass", "WaistCircumference"], (10, 100)),
]

# Analyses and their requirements as "domain:min_stars"
ANALYSES = [
    ("Sleep timing & duration trends ('later vs less' decomposition)", ["sleep:2"]),
    ("Sleep regularity & social jetlag", ["sleep:2"]),
    ("Recovery baseline (resting HR / HRV) + unexplained-period detection", ["cardio:2"]),
    ("Illness signatures (resting HR + respiratory rate + wrist temp)", ["cardio:2"]),
    ("Fitness trajectory (VO2max / pace) with sparse-data guards", ["cardio:1", "activity:1"]),
    ("Day-activity → night-sleep coupling", ["activity:2", "sleep:2"]),
    ("Strength & mobility proxies from gait (walking / stair speed)", ["gait:2"]),
    ("Hearing dose & loud-event audit", ["hearing:2"]),
    ("Cycle phase × recovery cross-analysis", ["cycle:1", "cardio:2"]),
    ("Workout history & training-load view", ["activity:1"]),
    ("Intervention testing ('did X help?')", ["cardio:1", "sleep:1"]),
    ("n-of-1 experiment design & tracking", ["cardio:1"]),
]

# Types whose raw values we sample to detect fraction-vs-percent storage
FRACTION_SUSPECTS = {
    "OxygenSaturation", "AppleWalkingSteadiness",
    "WalkingAsymmetryPercentage", "WalkingDoubleSupportPercentage",
}

STARS = {0: "\u2717  ", 1: "\u2605\u2606\u2606", 2: "\u2605\u2605\u2606", 3: "\u2605\u2605\u2605"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export_xml")
    ap.add_argument("--json", dest="json_out", default=None,
                    help="also write machine-readable inventory to this path")
    args = ap.parse_args()

    t0 = time.time()
    type_count = Counter()
    type_first = {}
    type_last = {}
    type_units = defaultdict(Counter)
    type_sources = defaultdict(Counter)
    value_samples = defaultdict(list)
    workout_types = Counter()
    workout_first, workout_last = None, None
    activity_summaries = 0
    me = {}
    export_date = None
    n = 0

    context = ET.iterparse(args.export_xml, events=("end",))
    for _, elem in context:
        tag = elem.tag
        if tag == "Record":
            n += 1
            t = short(elem.get("type", "?"))
            type_count[t] += 1
            sd = elem.get("startDate", "")[:10]
            if sd:
                if t not in type_first or sd < type_first[t]:
                    type_first[t] = sd
                if t not in type_last or sd > type_last[t]:
                    type_last[t] = sd
            u = elem.get("unit")
            if u:
                type_units[t][u] += 1
            src = elem.get("sourceName", "?")
            type_sources[t][src] += 1
            if t in FRACTION_SUSPECTS and len(value_samples[t]) < 200:
                try:
                    value_samples[t].append(float(elem.get("value")))
                except (TypeError, ValueError):
                    pass
            if n % 500000 == 0:
                print(f"  ...{n:,} records scanned ({time.time()-t0:.0f}s)",
                      file=sys.stderr)
            elem.clear()
        elif tag == "Workout":
            wt = elem.get("workoutActivityType", "?").replace(
                "HKWorkoutActivityType", "")
            workout_types[wt] += 1
            sd = elem.get("startDate", "")[:10]
            if sd:
                workout_first = min(workout_first or sd, sd)
                workout_last = max(workout_last or sd, sd)
            elem.clear()
        elif tag == "ActivitySummary":
            activity_summaries += 1
            elem.clear()
        elif tag == "Me":
            for k, v in elem.attrib.items():
                me[short(k.replace("HKCharacteristicTypeIdentifier", ""))] = v
        elif tag == "ExportDate":
            export_date = elem.get("value")

    total = sum(type_count.values())
    first = min(type_first.values()) if type_first else None
    last = max(type_last.values()) if type_last else None
    span_years = None
    if first and last:
        span_years = round((_days_between(first, last)) / 365.25, 1)

    # --- Domain ratings ---------------------------------------------------
    domains = []
    ratings = {}
    for key, label, members, (low, high) in DOMAINS:
        present = [t for t in members if type_count.get(t)]
        cnt = sum(type_count[t] for t in present)
        d_first = min((type_first[t] for t in present), default=None)
        d_last = max((type_last[t] for t in present), default=None)
        span_d = _days_between(d_first, d_last) if d_first and d_last else 0
        if cnt == 0:
            stars = 0
        elif cnt >= high and span_d >= 365:
            stars = 3
        elif cnt >= low and span_d >= 90:
            stars = 2
        else:
            stars = 1
        ratings[key] = stars
        domains.append({
            "key": key, "label": label, "stars": stars, "records": cnt,
            "types_present": present, "first": d_first, "last": d_last,
            "span_days": span_d,
        })

    # --- Unlocked analyses --------------------------------------------------
    unlocked, locked = [], []
    for name, reqs in ANALYSES:
        missing = []
        for r in reqs:
            dom, min_stars = r.split(":")
            if ratings.get(dom, 0) < int(min_stars):
                missing.append(dom)
        (unlocked if not missing else locked).append(
            {"name": name, "missing_domains": missing})

    # --- Trap detection -----------------------------------------------------
    traps = []

    def multi_source(t):
        srcs = type_sources.get(t, Counter())
        tot = sum(srcs.values())
        if tot == 0:
            return []
        return [s for s, c in srcs.items() if c / tot >= 0.10]

    ms = multi_source("StepCount")
    if len(ms) >= 2:
        traps.append({
            "id": "steps_double_count",
            "detail": f"StepCount written by {len(ms)} sources ({', '.join(ms)}). "
                      "Naive daily sums double-count; fix = per-day max of any "
                      "single source (build_daily.py applies this)."})
    ms = multi_source("SleepAnalysis")
    if len(ms) >= 2:
        traps.append({
            "id": "sleep_overlap",
            "detail": f"SleepAnalysis written by {len(ms)} sources ({', '.join(ms)}). "
                      "Overlapping segments inflate totals (classic '22h/night' bug); "
                      "fix = interval union merge (build_daily.py applies this)."})
    for t in ("ActiveEnergyBurned", "BasalEnergyBurned"):
        ms = multi_source(t)
        if len(ms) >= 2:
            traps.append({
                "id": f"{t}_multi_source",
                "detail": f"{t} written by {len(ms)} sources ({', '.join(ms)}). "
                          "Summing across sources inflates energy; fix = per-day "
                          "max single source (build_daily.py applies this)."})
    for t, vals in value_samples.items():
        if vals and sorted(vals)[len(vals) // 2] <= 1.5:
            traps.append({
                "id": f"{t}_fraction_storage",
                "detail": f"{t} stored as fraction (median sample "
                          f"{sorted(vals)[len(vals)//2]:.2f}) despite '%' unit; "
                          "fix = x100 (build_daily.py applies this)."})
    if type_count.get("TimeInDaylight"):
        traps.append({
            "id": "daylight_lux_sensor",
            "detail": "TimeInDaylight uses the ambient light sensor: bright indoor "
                      "light (e.g. 10,000-lux therapy lamps) counts as 'daylight'. "
                      "Interpretation caveat only; no numeric fix possible."})

    # --- Print skill tree -----------------------------------------------------
    print()
    print("YOUR DATA, MAPPED")
    print("=" * 60)
    if export_date:
        print(f"Export created : {export_date}")
    if first:
        print(f"Coverage       : {first} \u2192 {last} ({span_years} years)")
    print(f"Records        : {total:,} across {len(type_count)} types | "
          f"Workouts: {sum(workout_types.values()):,} | "
          f"Daily activity rings: {activity_summaries:,}")
    if me.get("DateOfBirth") or me.get("BiologicalSex"):
        sex = me.get("BiologicalSex", "").replace("HKBiologicalSex", "")
        dob = me.get("DateOfBirth", "?")
        print(f"Profile        : born {dob}, sex {sex or '?'}")
    print()
    print("SKILL TREE (what your data unlocks)")
    for d in sorted(domains, key=lambda x: -x["records"]):
        star = STARS[d["stars"]]
        if d["stars"] == 0:
            print(f"  {star} {d['label']:<38} \u2014 not recorded")
        else:
            print(f"  {star} {d['label']:<38} {d['records']:>9,} records | "
                  f"{d['first']} \u2192 {d['last']}")
    print()
    print(f"UNLOCKED ANALYSES ({len(unlocked)}/{len(ANALYSES)})")
    for a in unlocked:
        print(f"  \u2713 {a['name']}")
    for a in locked:
        print(f"  \u2717 {a['name']}  (needs: {', '.join(a['missing_domains'])})")
    print()
    if traps:
        print("DATA TRAPS DETECTED")
        for tr in traps:
            print(f"  \u26a0 {tr['detail']}")
        print()
    if workout_types:
        top = ", ".join(f"{k} x{v}" for k, v in workout_types.most_common(5))
        print(f"WORKOUTS: {top}")
        print()
    print(f"NEXT: python3 build_daily.py {args.export_xml} --out analysis/")
    print(f"[inventory done in {time.time()-t0:.0f}s]")

    if args.json_out:
        out = {
            "export_date": export_date,
            "coverage": {"first": first, "last": last, "span_years": span_years},
            "total_records": total,
            "profile": me,
            "record_types": {
                t: {"count": c, "first": type_first.get(t),
                    "last": type_last.get(t),
                    "units": dict(type_units.get(t, {})),
                    "sources": dict(type_sources.get(t, {}))}
                for t, c in type_count.most_common()},
            "domains": domains,
            "unlocked_analyses": [a["name"] for a in unlocked],
            "locked_analyses": [
                {"name": a["name"], "missing": a["missing_domains"]}
                for a in locked],
            "traps": traps,
            "workouts": {"types": dict(workout_types),
                         "first": workout_first, "last": workout_last},
            "activity_summaries": activity_summaries,
        }
        import os
        os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
        with open(args.json_out, "w") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
        print(f"[json written to {args.json_out}]")


def _days_between(a, b):
    from datetime import date
    ya, ma, da = int(a[:4]), int(a[5:7]), int(a[8:10])
    yb, mb, db = int(b[:4]), int(b[5:7]), int(b[8:10])
    return (date(yb, mb, db) - date(ya, ma, da)).days


if __name__ == "__main__":
    main()
