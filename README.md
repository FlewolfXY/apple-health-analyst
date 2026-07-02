# apple-health-analyst

[English](README.md) | [简体中文](README.zh-CN.md)

A Cursor Agent Skill for Apple Health exports.

It turns `export.xml` into a local, evidence-graded health analysis workspace:
first a report, then an analyst you can keep asking questions.

```text
You: analyze my Apple Health export

Agent:
  - maps which health domains your export can support
  - fixes common Apple Health data traps
  - builds a cleaned daily table
  - writes a first report
  - ends with questions you can answer or ask next
```

## Why This Is Useful

Apple Health exports are rich, but awkward:

- the raw file can contain millions of records;
- iPhone + Apple Watch can double-count steps, distance and energy;
- multiple sleep apps can overlap and create impossible totals;
- wearables can show that something changed, but not what happened in your life.

This skill gives the agent a repeatable workflow for turning that export into
an ongoing investigation. It is not a dashboard. It is a local analyst with
scripts, playbooks, memory files and rules about evidence.

## How It Differs From Health Apps

Most health apps are dashboards: they summarize your month, compare this year
with last year, and surface charts for sleep, HRV, activity or workouts.

This skill is closer to an analyst:

- it looks for unexplained periods, behavior shifts and cross-domain patterns;
- it asks for life context when the sensors can see *what* changed but not
  *why*;
- it can test user-supplied hypotheses such as "did this habit help?";
- it can say "this data cannot answer that" instead of forcing a weak answer;
- it leaves behind state, findings and experiment plans that future sessions
  can reuse.

The goal is not another monthly or yearly health recap. The goal is AI-assisted
mining and interpretation of personal health data.

## What You Get

During the first run, the agent creates an `analysis/` folder:

```text
analysis/
  daily.csv          # cleaned one-row-per-day table
  meta.json          # traps fixed, notable periods, behavior shifts
  inventory.json     # data coverage and unlocked analysis domains
  first_report.md    # first-pass report, written by the agent after setup
  STATE.md           # analyst memory
  findings.md        # append-only findings ledger
  events.csv         # life events supplied by the user
  experiments/       # n-of-1 experiment plans
```

The first report is designed to start a conversation. It includes:

- baseline numbers for sleep, recovery, activity and fitness;
- the strongest findings, each with an evidence grade;
- data-quality fixes with receipts;
- limits: what Apple Health can and cannot answer;
- suggested follow-up questions;
- unexplained periods or behavior changes where the agent asks for context.

## Example Output

The inventory step presents the export as capabilities:

```text
SKILL TREE
  ★★★ Activity & Energy
  ★★★ Cardiovascular & Recovery
  ★★★ Sleep
  ★★★ Gait & Mobility
  ★★★ Hearing Exposure
  ★★☆ Menstrual Cycle

DATA TRAPS DETECTED
  ⚠ StepCount written by multiple sources.
    Naive daily sums can double-count.
  ⚠ SleepAnalysis written by multiple apps.
    Overlapping segments must be union-merged.
```

The daily-table step also surfaces questions for the user:

```text
NOTABLE PERIODS
  ? 2025-12-23 → 2025-12-28:
    resting heart rate +14 bpm, HRV -6 ms

BEHAVIOR SHIFTS
  ? 2026-05:
    daylight minutes 29 → 154 per day
```

The agent does not assume what these mean. It asks: were you sick, traveling,
starting a new habit, changing your schedule? Your answer becomes structured
context for later analysis.

## Questions You Can Ask After Onboarding

```text
Why did my sleep get worse this year?
Did starting a light lamp help my sleep timing?
Was last month's fatigue visible in heart rate or HRV?
Do my workouts show real fitness improvement or just more measurements?
Design a 2-week experiment to test whether walking more improves my sleep.
What can this data not tell me?
```

## What Makes It Different

**Fresh computation, not model memory.** Every number must come from the local
CSV or a script run in the current session.

**Evidence grades.** Findings are labeled strong, moderate or weak so the user
knows how much to trust them.

**Confound checks.** Before/after claims must check season, trend, illness,
cycle phase and co-occurring life changes.

**Honest limits.** The skill is explicit about what wearables cannot measure:
nutrition, mood causes, muscle vs fat, blood biomarkers and many supplement
effects.

**Cold-start discipline.** The agent may only use the export and what the user
tells it. If it sees a behavior shift, it asks what happened instead of
inventing a story.

## Install

```bash
mkdir -p ~/.cursor/skills
git clone https://github.com/FlewolfXY/apple-health-analyst \
  ~/.cursor/skills/apple-health-analyst
```

## Use

1. On iPhone, open Health -> profile picture -> **Export All Health Data**.
2. Move the exported zip to your Mac and unzip it.
3. Open that folder in Cursor.
4. Ask: `analyze my Apple Health export`.

The skill runs locally. Under the hood:

```bash
python3 ~/.cursor/skills/apple-health-analyst/scripts/onboard.py \
  export.xml --out analysis/
```

The scripts use only the Python standard library and stream the XML, so
multi-GB exports are safe.

## Privacy

Your raw health export stays on your machine. The scripts do not use network
access. The repository also ignores `*.xml`, `*.zip` and `analysis/` so raw
health data and generated reports are not committed by accident.

## Current Coverage

- Sleep timing, duration, regularity and sleep inertia
- Resting heart rate, HRV, respiratory rate and recovery baselines
- Illness-like periods from multi-signal changes
- Activity, workouts and activity-sleep coupling
- Running speed, pace, power and stride metrics when present
- Heart-rate recovery and six-minute walk distance when present
- Gait and mobility proxies such as walking speed and stair-ascent speed
- Hearing exposure from headphone and environmental audio records
- Menstrual-cycle overlays when cycle data exists
- Intervention checks and n-of-1 experiment planning

## Roadmap

- Synthetic demo export and example report
- GPX workout-route maps
- Multi-export diffing: "what changed since my last export?"
- Better cycle-phase modeling
- Hearing-dose report using weekly exposure budgets
- Browser-free report preview

## Disclaimer

This is not medical advice. Consumer wearables estimate; this skill analyzes
patterns, not diagnoses. For concerning symptoms, talk to a clinician.

## License

MIT
