# Playbook: Sleep

## Columns & conventions (from daily.csv)

| Column | Meaning |
|---|---|
| `sleep_total_h` | union-merged asleep hours in the 18:00→18:00 window ending on this wake day (naps included) |
| `sleep_onset_hr` | first substantial (>=30 min) sleep of the night. Axis: hours since 00:00 of the *previous* day — 23.12 = 23:07 before midnight, **26.5 = 02:30 after midnight** |
| `sleep_wake_hr` | end of the longest block, hours since midnight of wake day |
| `sleep_midpoint_hr` | (onset + wake) / 2 on the onset axis |
| `sleep_anomaly` | 1 = night >12 h (over-detection: watch left on nightstand, sick day). **Exclude from all averages.** |

Always filter `sleep_anomaly != 1` before computing anything.

## Investigation recipes

**"My sleep got worse" — decompose first.** Worse = later? shorter? more
irregular? Compute per month: median onset, median total, std of onset. These
three move independently and have different fixes. The most common pattern in
night-owl data is *later, not less* — duration intact while timing drifts.
Saying which one it is, with numbers, is already more than most sleep apps do.

**Timing trend**: monthly or yearly median `sleep_onset_hr`. Report drift in
minutes/year. Check for a change point (largest single-month jump); if one
exists, ask the user what happened then — do not guess.

**Regularity / social jetlag**: std of onset per rolling 30 days; weekday vs
weekend midpoint gap. A gap > 1 h is meaningful ("social jetlag").

**Sleep inertia**: lag-1 autocorrelation of onset. Typical strong value
~0.5-0.7: one late night drags several. Useful, actionable framing: "protect
the first night after a late one."

**Drivers (what makes tonight early/late?)**: correlate candidate day-features
(steps, exercise_min, workout_min, daylight_min) against same-night onset and
next-day `hrv_sdnn_ms`. Rules:
- Spearman over Pearson (skewed data);
- n >= 60 pairs before reporting anything;
- cap grade at 🟡 — observational, confounded by weekday/season;
- never phrase as causation; offer as "strongest lever worth an experiment"
  and point to the intervention playbook to actually test it.

**Early-sleep payoff**: within-person comparison of nights with onset before
vs after the user's own median: HRV, resting HR next day. Same 🟡 cap.

## Traps

- **Multi-source overlap** is fixed upstream, but if numbers look insane
  (>14 h regularly), re-check `meta.json` traps before analyzing.
- **"Sleep less" headlines**: check `sleep_anomaly` exclusion and remember
  naps count in the total.
- **Season is a confound for everything sleep**: daylight, school/work
  calendar, and holidays all move onset. Any before/after comparison must
  note the season delta (intervention playbook).
- **Staging (deep/REM) is not in daily.csv by design** — consumer staging is
  epoch-level estimation; per-night deep-sleep minutes are not trustworthy
  enough to build findings on. Timing, duration and regularity are.

## Grading guide

- Multi-year timing drift with consistent yearly medians → 🟢
- Correlational drivers, within-person contrasts → 🟡 max
- Anything from <30 nights or a contaminated window → 🟠
