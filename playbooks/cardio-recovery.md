# Playbook: Cardio, Recovery, Fatigue & Illness

## What each signal is good for

| Column | Trust level | Notes |
|---|---|---|
| `resting_hr` | High (trend) | The single best recovery dial. Apple computes it daily from quiet moments. Baseline shifts of 3-5 bpm sustained over weeks are meaningful. |
| `hrv_sdnn_ms` | Medium | Spot samples, mostly nocturnal; noisy day-to-day. Only interpret >=14-day trends. Direction: higher = more recovered. |
| `resp_rate_brpm` | Medium | Sleep-measured. Very stable per person; sustained +1 brpm is a real signal (often illness). |
| `wrist_temp_c` | Medium | Nightly deviation from personal baseline; rises with illness, cycle phase, hot rooms. |
| `spo2_pct` | Low-medium | Wrist SpO2 is noisy; only flag sustained drops below ~94 across many nights. |
| `vo2max` | Trend only | **Estimated** — see the fake-decline trap below. |
| `walking_hr_avg` | Medium | Useful context for cardio efficiency during ordinary walking. |
| `heart_rate_recovery_1min` | Medium | Sparse but meaningful after workouts; higher recovery usually means better fitness. |
| `six_min_walk_m` | Medium | Mobility/cardio proxy. Coverage is often sparse; check `meta.json > columns`. |
| `running_speed_kmh` / `running_pace_min_km` / `running_power_w` | Medium | Workout-only. Use as supporting evidence for running progress, not whole-body fitness alone. |
| `hr_min/mean/max` | Context | Raw daily HR stats; hr_min ≈ crude RHR proxy when resting_hr missing. |

## Investigation recipes

**"Why am I so tired lately?" — fixed ladder, in order:**
1. **Window definition**: "lately" = last 14 days unless the user says
   otherwise. Compare against the trailing 60 days before that.
2. **Recovery check**: RHR delta, HRV delta vs baseline. Elevated RHR +
   depressed HRV = body under load; proceed. Flat = the fatigue is probably
   not visible to these sensors (say so — limits playbook).
3. **Illness signature**: RHR up **and** resp rate up **and** wrist temp up,
   concurrently → likely infection (past or brewing). Check for it explicitly
   before blaming lifestyle. Infections also show 1-2 weeks of elevated RHR
   *before* symptoms in some cases.
4. **Sleep debt & timing**: sleep totals and onset drift in the window
   (sleep playbook). Later-than-usual onset with normal duration still hurts.
5. **Cycle phase** (if `menstrual_flow` recorded): the 5 days before onset
   typically show lower HRV / higher RHR. Physiological, not a problem to fix.
6. **Life context**: check `events.csv`; if nothing explains it, tell the user
   what the sensors saw and **ask what was happening**. Their answer is data —
   record it in events.csv.

**Illness retrospective**: for a known sick date, plot RHR/resp/temp 3 weeks
around it; report peak deltas and days-to-baseline. Useful for "how hard did
that flu hit me" and for calibrating the user's trust in the signals.

**Fitness trajectory**: yearly means of vo2max + workout count + running
pace/speed/power (if present) + RHR/HRV. Three signals agreeing = 🟢. One
signal alone = 🟡 max. Always check `meta.json > columns` for sparse metrics
before leaning on them.

## The VO2max fake-decline trap (check before every fitness verdict)

Apple only updates VO2max during qualifying outdoor walks/runs. If the user
stopped running, the estimate both staleness-drifts and loses accuracy. Before
reporting a decline: count vo2max readings per year and workout frequency. If
readings collapsed together with training volume, report "decline confounded
with reduced training + fewer estimates" — grade 🟡 at best, and say the
honest version: *stopping running both lowers fitness and degrades the
measurement of it.*

## Grading guide

- Sustained multi-week RHR/HRV baseline shifts, corroborated by a second
  signal → 🟢
- Single-signal trends, cycle-phase effects → 🟡
- Anything inside an illness window or <14 days → 🟠
- Never diagnose. Sustained resting HR anomalies, chest pain, fainting →
  recommend a doctor.
