# Playbook: Onboarding (first run)

Goal: in one session, take the user from "here is my export" to (a) a first
report worth screenshotting and (b) the understanding that they can now ask
this analyst anything. The report is the welcome gift; the conversation is
the product.

## Steps

```
- [ ] 1. Locate the export & set expectations
- [ ] 2. Run inventory.py -> present the skill tree
- [ ] 3. Run build_daily.py; while it runs, interview the user
- [ ] 4. Create analysis/ state files
- [ ] 5. Mine findings: breadth first, then loudness
- [ ] 6. Write first_report.md (template below)
- [ ] 7. Hand over: guided questions + the data's questions back
```

### 1. Locate & set expectations

Find `export.xml` (unzip `export.zip` if needed; the file may be 1-3 GB).
Before parsing, tell the user, briefly:
- everything runs locally; only statistical aggregates enter the chat;
- the first pass takes a minute or two;
- at the end they get a report **and** a standing analyst they can question.

### 2. Inventory -> skill tree

```bash
python3 scripts/inventory.py export.xml --json analysis/inventory.json
```

Relay the skill tree **as capabilities, not record types**. Two rules:
- Lead with what is unlocked and strong, mention what is absent without blame.
- If traps were detected, mention 1-2 in one line each ("two apps write your
  sleep — naively summed that reads 20 h/night; I'll union-merge intervals").
  Showing a dodged trap is the cheapest way to earn trust. Do not lecture.

### 3. Build the daily table — and interview the user while it runs

```bash
python3 scripts/build_daily.py export.xml --out analysis/
```

The build takes a minute or two. Use that time for the **onboarding
interview** — three questions, no more (the user just arrived; don't make
them fill out a form):

1. *"What do you most want to understand about your body?"* → weights which
   domains get depth in the report.
2. *"Any big timeline events I should know about — moves, job changes,
   illnesses, relationships starting or ending?"* → seed `events.csv`.
3. *"Have you started or stopped anything you'd want tested — medication,
   supplements, a light lamp, a new mattress, an exercise habit?"* → these
   become the intervention questions in the report. **This is the only
   legitimate source of intervention dates besides the data itself.**

If the user is away or answers briefly, fine — the report template has an
interview section for async answers. Never invent or assume answers.

When the build finishes, relay `traps_applied` (numbers included, e.g. "naive
step summing would have inflated by 63%"). This is the last time cleaning is
mentioned; from here on it is silent infrastructure.

### 4. Create state files

- `analysis/STATE.md` — export path/date, rows, columns available, report
  path, "no open experiments".
- `analysis/findings.md` — header only.
- `analysis/events.csv` — header `date,event,category`; if the user has an
  existing events file, copy it in.

### 5. Mine findings: breadth first, then loudness

**Breadth rule: compute at least one candidate finding for every domain the
skill tree rated ★★☆ or better.** Then select the final 5-8 by (effect size x
confidence) — but the report must span at least 4 domains when the data
supports it. A rich export deserves a rich report; analyzing 3 domains of a
9-domain dataset makes the analyst look shallow. Query `analysis/daily.csv`.

Candidate recipes per domain:

- **Sleep drift**: median `sleep_onset_hr` per year. A shift >= 1 h across
  years is a headline. Decompose: did duration also fall, or only timing?
- **Sleep regularity / inertia**: rolling 30-day std of onset; lag-1
  autocorrelation; weekday-weekend midpoint gap (social jetlag).
- **Recovery trend**: yearly mean `resting_hr`, `hrv_sdnn_ms`, `vo2max`.
  Direction consistent across all three = strong; check workout frequency
  before calling a VO2max decline real (see cardio playbook).
- **Activity-sleep coupling**: correlation of `steps` vs same-night
  `sleep_onset_hr` and next-day `hrv_sdnn_ms` (see sleep playbook caps).
- **Gait / strength proxies**: yearly means of `walk_speed_kmh`,
  `stair_up_mps`, `step_length_cm`. Declining stair-ascent speed is a
  lower-body-strength flag (proxy — cap 🟡, see limits playbook).
- **Hearing**: median `headphone_db_avg` + mean `headphone_hours` per year vs
  the 60 dB guideline; count of high-dB days. **A clean bill of health is a
  reportable finding** — a report that only carries bad news reads as
  fearmongering, not honesty.
- **Cycle** (if `menstrual_flow` present, >= 6 cycles): HRV / resting HR in
  the 5 days before each period start vs all other days.
- **Notable periods**: `meta.json > notable_periods` — see step 7.
- **Behavior shifts**: `meta.json > behavior_changes` — regime jumps in
  habit-like metrics (daylight, steps, headphone hours...). These are the
  cold-start source for intervention questions: the data sees *what* changed;
  only the user knows *why*.

Grade every finding 🟢🟡🟠 per SKILL.md.

### 6. Write the report

Save as `analysis/first_report.md`. Keep it to one screenful per section.

**Tone rules (as binding as the numbers):**
- Warm but not familiar. You are a sharp analyst the user met an hour ago,
  not an old friend. No inside references, no assumed nicknames for life
  periods ("your crunch week", "your job hunt") unless the user used those
  words this session.
- **Provenance discipline** (iron law 9): every personalized statement must
  trace to a number computed this session or the user's own words this
  session. If neither, it does not enter the report. When the export sits in
  a workspace full of other context, that context does not exist for you.
- Curiosity over judgment: behavior shifts get asked about, never scolded.
- Good news is stated plainly, not buried.

```markdown
# Your body, according to {N} million data points

## 1 · Body ID card
{6-8 baseline numbers with context: resting HR, HRV, sleep midpoint & duration,
median daily steps (deduplicated), VO2max, walking speed. One line each:
value + what it means at this age/sex, hedged appropriately.}

## 2 · The {3-5} loudest things your data says
{One block per finding: verdict in bold, the 2-3 numbers that carry it,
evidence grade, one-line caveat if needed.}

## 3 · What I fixed and what I can't see
{2-4 bullets: traps auto-fixed (with inflation numbers).
2-4 bullets: what this data cannot answer (from limits playbook) — nutrition,
mood, muscle vs fat, blood biomarkers. Honesty section; keep it short.}

## 4 · Ask me — start with these
{4 questions generated from THIS user's findings, each copy-pasteable, each
exercising a different playbook. Format:
- 🌙 "..." (from finding #1 — trend investigation)
- 🫀 "..." (recovery/fatigue)
- 🧪 "..." (intervention — source the candidate ONLY from meta.json
  behavior_changes or from the user's interview answers. If neither exists,
  phrase it as a slot: "I started ___ on ___ — did it do anything?")
- 🔬 "Design an experiment to test whether ..." (n-of-1, anchored to one of
  their actual findings)}

## 5 · Your data has questions for you
{Two sources, both purely data-derived:
a) meta.json notable_periods — minus any matching an illness signature
   (RHR + resp rate + wrist temp all up -> say "this looks like an
   infection; do you remember one?" instead of an open question) and minus
   any the user already explained in the interview.
b) meta.json behavior_changes — "around {month}, your {metric} jumped
   {before} → {after}. I can see WHAT changed, not WHY. What was that?"
For each: the sensors saw your body/behavior change and can't see why. The
user's answer becomes events.csv data.}

## 6 · Three questions I'd still love answered
{The interview questions from step 3 that the user hasn't answered yet, if
any — phrased for async reply. Skip this section if all were answered.}

*Not medical advice. Sensors estimate; trends over points.*
```

Personalized beats canned: every guided question must reference the user's own
numbers or dates. A generic question menu is an FAQ; a personal one is a hook.

### 7. Hand over

End the session by saying, in your own words: the report is the snapshot; the
analyst is standing. Anything they wonder about their body is now a question
they can just ask. Update `STATE.md`.
