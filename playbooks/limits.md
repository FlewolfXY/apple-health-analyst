# Playbook: Limits — what this data cannot answer

An analyst that knows its blind spots is worth more than one that answers
everything. When a question lands here, say clearly: (1) not measurable with
this data, (2) why, (3) what instrument *would* measure it. Never soft-answer
around a blind spot.

## Not measurable (the honest list)

| Question | Why not | What would measure it |
|---|---|---|
| What/how much you ate | No nutrition records unless manually logged; energy burn is a model, not intake | Food logging, photos, CGM for glucose response |
| Mood, stress *causes* | Sensors see physiological arousal (RHR up, HRV down) — excitement, anxiety and caffeine look identical | Subjective log alongside the sensors (offer to set one up: `analysis/subjective_log.csv`) |
| Muscle vs fat composition | Weight isn't body composition; wearables don't see tissue | BIA scale / DEXA; gait metrics (walking speed, stair speed, step length) are honest *proxies* for lower-body strength — offer these instead |
| Blood biomarkers (vitamin D, iron, hormones, HbA1c) | Not on the sensor path at all | Blood tests. Wearables cannot verify supplement repletion |
| Movement quality / exercise form | Only energy and heart rate are recorded, not kinematics | Video analysis, a coach |
| Blood pressure | Not measured by Apple Watch | A cuff |
| Whether a supplement "worked" (most) | Most targets (eyes, skin, immunity, cognition) have no wearable endpoint | Depends on target; often blood tests or nothing consumer-grade |
| Why you woke at 3 AM on one specific night | Single-night staging is noise-level | Only patterns across many nights count |

## Device error notes (calibrate trust, don't destroy it)

- **Sleep staging** (deep/REM minutes): epoch-level estimation; do not build
  findings on per-night stage minutes. Timing/duration/regularity are solid.
- **HRV (SDNN)**: spot samples mostly during sleep; huge day-to-day variance.
  Trends >=2 weeks only.
- **Optical HR**: excellent at rest, degrades during high-intensity intervals
  and in cold weather.
- **Calories** (active/basal): model outputs, not measurements. Fine for
  within-person trends, meaningless as absolute truth.
- **TimeInDaylight**: ambient light sensor — a bright lamp counts as daylight;
  contains no UVB/vitamin-D information.
- **VO2max**: estimated only during qualifying outdoor workouts; sparse
  readings fake declines (see cardio playbook).

## The mantra

Trends over points. Within-person over population norms. And when the sensors
can't see it: *say so, name the instrument that can, and — where a subjective
log would unlock the question — offer to start one.*
