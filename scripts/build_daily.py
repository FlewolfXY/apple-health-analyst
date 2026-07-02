#!/usr/bin/env python3
"""
build_daily.py -- Build a cleaned one-row-per-day wide table from an Apple
Health export. This is the analyst's index: every downstream question is
answered from daily.csv, never by re-parsing the XML.

Cleaning applied automatically (each fix is reported in meta.json):
  * Steps / distance / energy / flights: per-day per-source totals, then take
    the MAX single source (kills iPhone+Watch double counting).
  * Sleep: union-merge overlapping segments from all sources (kills the
    '22 hours of sleep' multi-app bug); nights >12h flagged, not dropped.
  * Fraction-stored percentages (SpO2 0.98 -> 98%): auto-detected and scaled.
  * Units normalized to metric (mi->km, in->cm, ft/s->m/s, degF->degC).
  * Audio exposure: duration-weighted energy average (dB are logs; a plain
    mean of dB values is wrong).

Also detects "notable periods": multi-day stretches where resting HR runs
above its trailing 60-day baseline -- material for the analyst to ask the
user about ("what was happening in your life then?").

Usage:
    python3 build_daily.py /path/to/export.xml --out analysis/

Outputs: analysis/daily.csv, analysis/meta.json.  Stdlib only.
"""

import argparse
import csv
import json
import os
import statistics
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

Q = "HKQuantityTypeIdentifier"
C = "HKCategoryTypeIdentifier"

ASLEEP_VALUES = {
    "HKCategoryValueSleepAnalysisAsleep",
    "HKCategoryValueSleepAnalysisAsleepUnspecified",
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
}

# Per-day per-source SUM, then max across sources
SUM_MAX_TYPES = {
    Q + "StepCount": "steps",
    Q + "DistanceWalkingRunning": "distance_km",
    Q + "DistanceCycling": "cycling_km",
    Q + "FlightsClimbed": "flights",
    Q + "ActiveEnergyBurned": "active_kcal",
    Q + "BasalEnergyBurned": "basal_kcal",
    Q + "AppleExerciseTime": "exercise_min",
    Q + "AppleStandTime": "stand_min",
    Q + "TimeInDaylight": "daylight_min",
}

# Per-day MEAN across all records
MEAN_TYPES = {
    Q + "HeartRateVariabilitySDNN": "hrv_sdnn_ms",
    Q + "RespiratoryRate": "resp_rate_brpm",
    Q + "OxygenSaturation": "spo2_pct",
    Q + "WalkingSpeed": "walk_speed_kmh",
    Q + "WalkingStepLength": "step_length_cm",
    Q + "WalkingDoubleSupportPercentage": "double_support_pct",
    Q + "WalkingAsymmetryPercentage": "walk_asymmetry_pct",
    Q + "AppleWalkingSteadiness": "walking_steadiness_pct",
    Q + "StairAscentSpeed": "stair_up_mps",
    Q + "StairDescentSpeed": "stair_down_mps",
    Q + "PhysicalEffort": "physical_effort_met",
}

# Per-day LAST value
LAST_TYPES = {
    Q + "RestingHeartRate": "resting_hr",
    Q + "VO2Max": "vo2max",
}

FRACTION_SUSPECT_COLS = {"spo2_pct", "double_support_pct",
                         "walk_asymmetry_pct", "walking_steadiness_pct"}

UNIT_FACTORS = {"mi": 1.609344, "mi/hr": 1.609344, "in": 2.54,
                "ft/s": 0.3048, "km": 1.0, "km/hr": 1.0, "cm": 1.0,
                "m/s": 1.0}

COLUMNS = [
    "date",
    "sleep_total_h", "sleep_onset_hr", "sleep_wake_hr", "sleep_midpoint_hr",
    "sleep_anomaly",
    "resting_hr", "hr_min", "hr_mean", "hr_max", "hrv_sdnn_ms",
    "resp_rate_brpm", "spo2_pct", "wrist_temp_c",
    "steps", "distance_km", "cycling_km", "flights",
    "active_kcal", "basal_kcal", "exercise_min", "stand_min",
    "physical_effort_met",
    "walk_speed_kmh", "step_length_cm", "double_support_pct",
    "walk_asymmetry_pct", "walking_steadiness_pct",
    "stair_up_mps", "stair_down_mps",
    "headphone_db_avg", "headphone_hours", "env_db_avg",
    "daylight_min", "mindful_min", "menstrual_flow", "vo2max",
    "workout_count", "workout_min", "workout_types",
]


def pdt(s):
    """'2021-07-29 08:14:23 +0800' -> naive local datetime (fast path)."""
    return datetime(int(s[0:4]), int(s[5:7]), int(s[8:10]),
                    int(s[11:13]), int(s[14:16]), int(s[17:19]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export_xml")
    ap.add_argument("--out", default="analysis",
                    help="output directory (default: analysis/)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    t0 = time.time()
    sum_src = defaultdict(float)          # (col, day, source) -> sum
    mean_acc = defaultdict(lambda: [0.0, 0])   # (col, day) -> [sum, n]
    last_val = {}                          # (col, day) -> value
    hr_day = {}                            # day -> [min, max, sum, n]
    wrist_acc = defaultdict(lambda: [0.0, 0])  # day -> [sum, n]
    audio = defaultdict(lambda: [0.0, 0.0, 0.0])  # (col,day)->[energy,dur_s,max]
    sleep_intervals = []                   # (start_dt, end_dt)
    sleep_sources = Counter()
    mens_day = {}
    mindful = defaultdict(float)
    workouts = defaultdict(lambda: [0, 0.0, Counter()])  # day->[n,min,types]
    n = 0

    context = ET.iterparse(args.export_xml, events=("end",))
    for _, elem in context:
        tag = elem.tag
        if tag == "Record":
            n += 1
            if n % 500000 == 0:
                print(f"  ...{n:,} records ({time.time()-t0:.0f}s)",
                      file=sys.stderr)
            t = elem.get("type", "")
            sd = elem.get("startDate", "")
            day = sd[:10]

            if t in SUM_MAX_TYPES:
                try:
                    v = float(elem.get("value"))
                except (TypeError, ValueError):
                    elem.clear()
                    continue
                v *= UNIT_FACTORS.get(elem.get("unit"), 1.0) \
                    if SUM_MAX_TYPES[t] in ("distance_km", "cycling_km") else 1.0
                sum_src[(SUM_MAX_TYPES[t], day,
                         elem.get("sourceName", "?"))] += v
            elif t == Q + "HeartRate":
                try:
                    v = float(elem.get("value"))
                except (TypeError, ValueError):
                    elem.clear()
                    continue
                s = hr_day.get(day)
                if s is None:
                    hr_day[day] = [v, v, v, 1]
                else:
                    if v < s[0]:
                        s[0] = v
                    if v > s[1]:
                        s[1] = v
                    s[2] += v
                    s[3] += 1
            elif t in MEAN_TYPES:
                try:
                    v = float(elem.get("value"))
                except (TypeError, ValueError):
                    elem.clear()
                    continue
                u = elem.get("unit")
                if u in UNIT_FACTORS:
                    v *= UNIT_FACTORS[u]
                a = mean_acc[(MEAN_TYPES[t], day)]
                a[0] += v
                a[1] += 1
            elif t in LAST_TYPES:
                try:
                    last_val[(LAST_TYPES[t], day)] = float(elem.get("value"))
                except (TypeError, ValueError):
                    pass
            elif t == C + "SleepAnalysis":
                if elem.get("value") in ASLEEP_VALUES:
                    try:
                        s_dt = pdt(elem.get("startDate"))
                        e_dt = pdt(elem.get("endDate"))
                    except (TypeError, ValueError):
                        elem.clear()
                        continue
                    if e_dt > s_dt:
                        sleep_intervals.append((s_dt, e_dt))
                        sleep_sources[elem.get("sourceName", "?")] += 1
            elif t in (Q + "HeadphoneAudioExposure",
                       Q + "EnvironmentalAudioExposure"):
                try:
                    db = float(elem.get("value"))
                    s_dt = pdt(elem.get("startDate"))
                    e_dt = pdt(elem.get("endDate"))
                except (TypeError, ValueError):
                    elem.clear()
                    continue
                dur = max((e_dt - s_dt).total_seconds(), 30.0)
                col = ("headphone" if "Headphone" in t else "env")
                a = audio[(col, day)]
                a[0] += dur * 10 ** (db / 10.0)
                a[1] += dur
                if db > a[2]:
                    a[2] = db
            elif t == Q + "AppleSleepingWristTemperature":
                try:
                    v = float(elem.get("value"))
                    ed = elem.get("endDate", sd)[:10]
                except (TypeError, ValueError):
                    elem.clear()
                    continue
                if elem.get("unit") == "degF":
                    v = (v - 32) * 5 / 9
                a = wrist_acc[ed]
                a[0] += v
                a[1] += 1
            elif t == C + "MenstrualFlow":
                val = elem.get("value", "")
                if val and not val.endswith("None"):
                    mens_day[day] = val.replace(
                        "HKCategoryValueMenstrualFlow", "").lower()
            elif t == C + "MindfulSession":
                try:
                    s_dt = pdt(elem.get("startDate"))
                    e_dt = pdt(elem.get("endDate"))
                    mindful[day] += (e_dt - s_dt).total_seconds() / 60.0
                except (TypeError, ValueError):
                    pass
            elem.clear()
        elif tag == "Workout":
            day = elem.get("startDate", "")[:10]
            if day:
                w = workouts[day]
                w[0] += 1
                try:
                    dur = float(elem.get("duration"))
                except (TypeError, ValueError):
                    dur = 0.0
                w[1] += dur
                w[2][elem.get("workoutActivityType", "?").replace(
                    "HKWorkoutActivityType", "")] += 1
            elem.clear()
        elif tag in ("ActivitySummary", "Me", "ExportDate"):
            elem.clear()

    print(f"  parse done: {n:,} records in {time.time()-t0:.0f}s",
          file=sys.stderr)
    traps_applied = []

    # --- SUM_MAX collapse: per day take max single source -------------------
    day_vals = defaultdict(dict)  # day -> {col: value}
    per_day_source = defaultdict(lambda: defaultdict(dict))
    for (col, day, src), v in sum_src.items():
        per_day_source[col][day][src] = v
    for col, days in per_day_source.items():
        raw_total = dedup_total = 0.0
        multi_days = 0
        for day, srcs in days.items():
            raw = sum(srcs.values())
            best = max(srcs.values())
            raw_total += raw
            dedup_total += best
            if len(srcs) > 1:
                multi_days += 1
            day_vals[day][col] = best
        if multi_days and raw_total > dedup_total * 1.05:
            infl = (raw_total / dedup_total - 1) * 100
            traps_applied.append(
                f"{col}: {multi_days} multi-source days; per-day max-source "
                f"dedup applied (naive summing would inflate by {infl:.0f}%)")

    # --- Means / lasts / HR / wrist temp / audio / misc ----------------------
    frac_medians = {}
    frac_values = defaultdict(list)
    for (col, day), (s, cnt) in mean_acc.items():
        v = s / cnt
        day_vals[day][col] = v
        if col in FRACTION_SUSPECT_COLS and len(frac_values[col]) < 500:
            frac_values[col].append(v)
    for col, vals in frac_values.items():
        med = statistics.median(vals)
        frac_medians[col] = med
        if med <= 1.5:
            for day in list(day_vals):
                if col in day_vals[day]:
                    day_vals[day][col] *= 100
            traps_applied.append(
                f"{col}: stored as fraction (median {med:.2f}); scaled x100")
    for (col, day), v in last_val.items():
        day_vals[day][col] = v
    for day, (mn, mx, s, cnt) in hr_day.items():
        day_vals[day]["hr_min"] = mn
        day_vals[day]["hr_max"] = mx
        day_vals[day]["hr_mean"] = s / cnt
    for day, (s, cnt) in wrist_acc.items():
        day_vals[day]["wrist_temp_c"] = s / cnt
    for (col, day), (energy, dur, mx) in audio.items():
        import math
        if dur > 0:
            day_vals[day][f"{col}_db_avg"] = 10 * math.log10(energy / dur)
        if col == "headphone":
            day_vals[day]["headphone_hours"] = dur / 3600.0
    for day, v in mindful.items():
        day_vals[day]["mindful_min"] = v
    for day, v in mens_day.items():
        day_vals[day]["menstrual_flow"] = v
    for day, (cnt, mins, types) in workouts.items():
        day_vals[day]["workout_count"] = cnt
        day_vals[day]["workout_min"] = mins
        day_vals[day]["workout_types"] = "+".join(sorted(types))

    # --- Sleep: union merge, then assign to wake-day window ------------------
    n_sleep_nights = 0
    if sleep_intervals:
        sleep_intervals.sort()
        merged = []
        for s_dt, e_dt in sleep_intervals:
            if merged and s_dt <= merged[-1][1] + timedelta(minutes=1):
                if e_dt > merged[-1][1]:
                    merged[-1][1] = e_dt
            else:
                merged.append([s_dt, e_dt])
        if len(sleep_sources) >= 2:
            traps_applied.append(
                f"sleep: {len(sleep_sources)} sources "
                f"({', '.join(sleep_sources)}); union-merged "
                f"{len(sleep_intervals):,} segments into {len(merged):,}")
        nights = defaultdict(list)
        for s_dt, e_dt in merged:
            sleep_date = e_dt.date() if e_dt.hour < 18 \
                else e_dt.date() + timedelta(days=1)
            nights[sleep_date].append((s_dt, e_dt))
        anomalies = 0
        for sleep_date, ivs in nights.items():
            day = sleep_date.isoformat()
            total_h = sum((e - s).total_seconds() for s, e in ivs) / 3600.0
            axis0 = datetime.combine(sleep_date - timedelta(days=1),
                                     datetime.min.time())
            # onset: earliest >=30min interval starting before 10:00 wake-day
            candidates = [
                (s - axis0).total_seconds() / 3600.0
                for s, e in ivs
                if (e - s).total_seconds() >= 1800
                and (s - axis0).total_seconds() / 3600.0 < 34.0]
            main_s, main_e = max(ivs, key=lambda ie: ie[1] - ie[0])
            wake_axis = (main_e - axis0).total_seconds() / 3600.0
            d = day_vals[day]
            d["sleep_total_h"] = total_h
            if candidates:
                onset = min(candidates)
                d["sleep_onset_hr"] = onset
                d["sleep_midpoint_hr"] = (onset + wake_axis) / 2
            d["sleep_wake_hr"] = wake_axis - 24.0
            d["sleep_anomaly"] = 1 if total_h > 12.0 else 0
            anomalies += d["sleep_anomaly"]
            n_sleep_nights += 1
        if anomalies:
            traps_applied.append(
                f"sleep: {anomalies} nights >12h flagged sleep_anomaly=1 "
                "(over-detection; exclude from averages)")

    # --- Write CSV over continuous date range --------------------------------
    valid_days = [d for d in day_vals
                  if d[:2] == "20" and len(d) == 10]
    d0 = min(valid_days)
    d1 = max(valid_days)
    cur = date(int(d0[:4]), int(d0[5:7]), int(d0[8:10]))
    end = date(int(d1[:4]), int(d1[5:7]), int(d1[8:10]))
    csv_path = os.path.join(args.out, "daily.csv")
    nonnull = Counter()
    rows = 0
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        while cur <= end:
            day = cur.isoformat()
            vals = day_vals.get(day, {})
            row = [day]
            for col in COLUMNS[1:]:
                v = vals.get(col)
                if v is None:
                    row.append("")
                else:
                    nonnull[col] += 1
                    row.append(round(v, 2) if isinstance(v, float) else v)
            w.writerow(row)
            rows += 1
            cur += timedelta(days=1)

    # --- Notable periods: resting HR above trailing 60-day baseline ----------
    notable = _notable_periods(day_vals, d0, d1)

    # --- Behavior shifts: regime changes in habit-like metrics ---------------
    behavior = _behavior_changes(day_vals, d0, d1)

    meta = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "export_path": os.path.abspath(args.export_xml),
        "rows": rows,
        "date_range": {"first": d0, "last": d1},
        "sleep_nights": n_sleep_nights,
        "columns_nonnull": dict(nonnull),
        "traps_applied": traps_applied,
        "notable_periods": notable,
        "behavior_changes": behavior,
        "conventions": {
            "sleep_onset_hr": "hours since 00:00 of the PREVIOUS day: 23.12 = "
                              "23:07 before midnight, 26.5 = 02:30 after. "
                              "Night window = 18:00 to 18:00; attributed to "
                              "wake day.",
            "sleep_wake_hr": "hours since 00:00 of the wake day (end of the "
                             "longest sleep block)",
            "audio_db": "duration-weighted energy average (not plain dB mean)",
            "units": "metric everywhere: km, km/h, cm, m/s, degC, kcal",
        },
    }
    meta_path = os.path.join(args.out, "meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)

    print(f"\nWrote {csv_path} ({rows:,} days x {len(COLUMNS)} cols)")
    print(f"Wrote {meta_path}")
    if traps_applied:
        print("\nTRAPS AUTO-FIXED:")
        for t in traps_applied:
            print(f"  \u2713 {t}")
    if notable:
        print(f"\nNOTABLE PERIODS (resting HR above baseline; ask the user "
              f"what was happening):")
        for p in notable:
            print(f"  ? {p['start']} \u2192 {p['end']} ({p['days']}d): "
                  f"RHR +{p['rhr_delta']:.1f} bpm"
                  + (f", HRV {p['hrv_delta']:+.1f} ms" if p.get("hrv_delta")
                     is not None else ""))
    if behavior:
        print(f"\nBEHAVIOR SHIFTS (the data sees WHAT changed, the user knows "
              f"WHY; ask them):")
        for b in behavior:
            print(f"  ? {b['month']}: {b['metric']} {b['before']} \u2192 "
                  f"{b['after']} ({b['kind']})")
    print(f"\n[done in {time.time()-t0:.0f}s]")


BEHAVIOR_SUM_COLS = ["steps", "exercise_min", "daylight_min",
                     "headphone_hours", "mindful_min", "workout_min",
                     "cycling_km"]
BEHAVIOR_VAL_COLS = ["headphone_db_avg"]


def _behavior_changes(day_vals, d0, d1):
    """Regime shifts in habit-like metrics: months whose level jumps >=50%
    vs the prior 3-month mean. These are cold-start question hooks -- the
    data sees WHAT changed; only the user knows WHY. Guards: birth month of
    each metric skipped (sensor introduction is not a habit change), partial
    first/last months excluded."""
    cur = date(int(d0[:4]), int(d0[5:7]), int(d0[8:10]))
    end = date(int(d1[:4]), int(d1[5:7]), int(d1[8:10]))
    month_days = Counter()
    acc = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))
    while cur <= end:
        m = cur.isoformat()[:7]
        month_days[m] += 1
        vals = day_vals.get(cur.isoformat(), {})
        for col in BEHAVIOR_SUM_COLS + BEHAVIOR_VAL_COLS:
            v = vals.get(col)
            if v is not None:
                a = acc[col][m]
                a[0] += v
                a[1] += 1
        cur += timedelta(days=1)
    full_months = [m for m in sorted(month_days) if month_days[m] >= 25]
    out = []
    for col in BEHAVIOR_SUM_COLS + BEHAVIOR_VAL_COLS:
        series = []
        born = False
        for m in full_months:
            s, cnt = acc[col].get(m, [0.0, 0])
            if not born:
                if cnt > 0:
                    born = True  # skip the birth month itself
                continue
            if col in BEHAVIOR_VAL_COLS:
                if cnt >= 8:
                    series.append((m, s / cnt))
            else:
                series.append((m, s / month_days[m]))
        if len(series) < 6:
            continue
        vals_only = sorted(v for _, v in series)
        p10 = vals_only[int(0.1 * (len(vals_only) - 1))]
        p90 = vals_only[int(0.9 * (len(vals_only) - 1))]
        rng = p90 - p10
        if rng <= 0:
            continue
        seq = [v for _, v in series]
        cands = []
        for i in range(3, len(series)):
            prev = statistics.mean(seq[i - 3:i])
            nxt = statistics.mean(seq[i:i + 2])
            delta = nxt - prev
            norm = abs(delta) / rng          # effect vs the metric's own range
            rel = delta / max(abs(prev), 1e-9)
            if norm >= 0.5 and abs(rel) >= 0.5:
                cands.append((norm, series[i][0], prev, nxt, rel, i))
        cands.sort(reverse=True)
        kept = []
        for c in cands:
            if all(abs(c[5] - k[5]) > 4 for k in kept):
                kept.append(c)
        for norm, m, prev, nxt, rel, _i in kept[:2]:
            if prev < 0.05 * rng:
                kind = "started"
            elif nxt < 0.05 * rng:
                kind = "stopped"
            else:
                kind = "shift"
            out.append({"metric": col, "month": m, "kind": kind,
                        "before": round(prev, 1), "after": round(nxt, 1),
                        "change_pct": max(-999, min(999, int(round(rel * 100)))),
                        "effect": round(norm, 2)})
    out.sort(key=lambda x: -x["effect"])
    out = out[:8]
    out.sort(key=lambda x: x["month"])
    return out


def _notable_periods(day_vals, d0, d1, min_delta=4.0, min_days=4):
    """Stretches where resting HR runs >= min_delta bpm above the median of
    the trailing 60 days with data. Returns up to 8, largest first."""
    series = []
    cur = date(int(d0[:4]), int(d0[5:7]), int(d0[8:10]))
    end = date(int(d1[:4]), int(d1[5:7]), int(d1[8:10]))
    while cur <= end:
        day = cur.isoformat()
        v = day_vals.get(day, {}).get("resting_hr")
        if v is not None:
            series.append((cur, v))
        cur += timedelta(days=1)
    if len(series) < 90:
        return []
    flagged = []
    for i in range(60, len(series)):
        base = statistics.median(v for _, v in series[i - 60:i])
        d, v = series[i]
        if v >= base + min_delta:
            flagged.append((d, v - base, i))
    if not flagged:
        return []
    periods = []
    run = [flagged[0]]
    for item in flagged[1:]:
        if (item[0] - run[-1][0]).days <= 2:
            run.append(item)
        else:
            periods.append(run)
            run = [item]
    periods.append(run)
    out = []
    for run in periods:
        if len(run) < min_days:
            continue
        deltas = [r[1] for r in run]
        i_start, i_end = run[0][2], run[-1][2]
        hrv_delta = None
        hrv_in = [day_vals.get(d.isoformat(), {}).get("hrv_sdnn_ms")
                  for d, _, _ in run]
        hrv_in = [x for x in hrv_in if x is not None]
        hrv_base = [day_vals.get(series[j][0].isoformat(), {}).get(
            "hrv_sdnn_ms") for j in range(max(0, i_start - 60), i_start)]
        hrv_base = [x for x in hrv_base if x is not None]
        if len(hrv_in) >= 3 and len(hrv_base) >= 10:
            hrv_delta = statistics.mean(hrv_in) - statistics.mean(hrv_base)
        out.append({
            "start": run[0][0].isoformat(),
            "end": run[-1][0].isoformat(),
            "days": (run[-1][0] - run[0][0]).days + 1,
            "rhr_delta": round(statistics.mean(deltas), 1),
            "hrv_delta": round(hrv_delta, 1) if hrv_delta is not None else None,
            "score": round(statistics.mean(deltas) * len(run), 1),
        })
    out.sort(key=lambda p: -p["score"])
    return out[:8]


if __name__ == "__main__":
    main()
