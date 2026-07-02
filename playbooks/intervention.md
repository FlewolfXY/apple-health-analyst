# Playbook: Interventions & n-of-1 Experiments

The most common question ("I changed X — did it work?") and the easiest place
to produce confident nonsense. This checklist exists because every shortcut
below has produced a wrong answer at least once.

## Part A — Retrospective: "Did X help?"

### Gate 0: Can this data even measure it?

Before touching numbers: what is X *supposed* to change, and does any daily.csv
column sit on that causal path? A supplement targeting eyes/skin/immunity has
no wearable-visible endpoint — say so and stop. Do not run the analysis and
report "no effect" when the honest statement is "not measurable here"
(limits playbook). These are different answers.

### The checklist (all five, every time)

```
- [ ] 1. SEASON     compare same season if possible; else name the season delta
- [ ] 2. TREND      was the metric already moving before X? (pre-window slope)
- [ ] 3. CONTAMINATION  illness / travel / exam weeks inside either window?
                    (events.csv + meta.json notable_periods)
- [ ] 4. CYCLE      windows aligned to different cycle phases? (if tracked)
- [ ] 5. CO-CHANGES what else changed at the same time? Ask the user directly:
                    "what else was different after DATE?"
```

### Procedure

1. Pin the intervention date and windows: >=14 days each side, excluding
   contaminated days. If fewer than ~10 clean days per side, say the window is
   too dirty for a verdict (🟠 at best) — offer a prospective experiment
   instead (Part B).
2. Pick <=3 endpoint metrics **before** looking at outcomes, matched to the
   mechanism (earlier sleep → onset, HRV, RHR; not "everything").
3. Compare: effect size in real units first (minutes, bpm, ms), then a sanity
   check that it exceeds day-to-day noise (rough rule: |Δ| > 0.5 × within-
   window std, or a rank test if you want to be formal).
4. Run the checklist. Every unchecked box caps the grade at 🟡; two or more
   caps at 🟠.
5. Verdict in plain language + grade + caveats. Append to `findings.md`.

A negative result is a finding. Report "no detectable effect" with the same
confidence machinery, and distinguish it from "not measurable".

## Part B — Prospective: design an n-of-1 experiment

When the user wants to *test* something (or Part A returned "window too
dirty"), design it properly:

1. **One variable.** If they want to change three things, pick the one they
   care most about; the others wait.
2. **Pre-register** in `analysis/experiments/<name>.md`:
   - hypothesis, mechanism, endpoint metrics (<=3), expected direction
   - baseline window (>=14 days, may use existing data if clean)
   - intervention window (>=14 days)
   - evaluation date (put it in STATE.md — this is the return appointment)
   - abort criteria (feels bad, life event contaminates the window)
3. **ABAB beats AB** when the intervention is cheap to toggle (earplugs,
   shower timing, late caffeine). Two on-off cycles kill most seasonal and
   trend confounds. For slow interventions (training, supplements with
   loading), AB is acceptable — say the design is weaker.
4. **On evaluation day**: run Part A mechanics on the pre-registered metrics
   only. No post-hoc endpoint shopping: if the pre-registered metrics are
   null but something else moved, that is a new hypothesis (🟠), not a result.

## Phrasing verdicts

- 🟢 "X moved your onset earlier by ~40 min; survived season and trend checks."
- 🟡 "Suggestive drop in RHR after X, but the window overlaps your travel week."
- 🟠 "The window is contaminated by the flu; I can't honestly attribute this.
  Want to re-run it as a clean 2-week experiment?"
