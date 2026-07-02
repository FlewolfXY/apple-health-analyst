# apple-health-analyst

**An agent skill that turns Cursor into your personal health-data analyst.**
Feed it your Apple Health export; get a standing analyst you can interrogate —
not a one-shot report.

[中文说明](#中文说明) below.

---

## Why this exists

Your Apple Watch has been quietly recording millions of data points about your
body for years. Most tools that touch that export do one of two things: dump
charts on you, or silently compute wrong numbers (double-counted steps,
"22 hours of sleep" from overlapping apps). Both are report generators. A
report answers the questions it was written for; your body will raise new ones
next week.

This skill takes the other path: after a one-time onboarding, the agent holds
an **ongoing, honest investigation** into your data. You ask questions in
plain language; it answers with fresh computation, evidence grades, and — when
your data genuinely can't answer — an honest *"this isn't measurable here,
and here's what would measure it."*

## What it does

- **Onboarding**: streams your `export.xml` (multi-GB safe, stdlib only,
  ~1 min), maps what your data unlocks as a skill tree, auto-fixes known data
  traps, builds a cleaned one-row-per-day table, and writes a first report.
- **The report ends with questions, in both directions**: guided questions
  generated from *your* findings (copy-paste one to continue), and questions
  your data asks *you* — unexplained periods where your body was visibly under
  load and the sensors can't see why. Your answer becomes data.
- **Ongoing analysis**: sleep timing/regularity, recovery baselines, illness
  signatures, fitness trajectory, activity-sleep coupling, gait-based strength
  proxies — each backed by a playbook that encodes the traps.
- **Intervention testing**: "I started X — did it work?" runs through a
  mandatory confound checklist (season, trend, contamination, cycle,
  co-changes). It will refuse to give a verdict from a dirty window and offer
  a properly designed n-of-1 experiment instead.
- **Memory**: findings accumulate in an append-only ledger; experiments are
  pre-registered with evaluation dates; a new session picks up where the last
  one ended.

## What makes it different

1. **Evidence grades on everything** (🟢 strong / 🟡 moderate / 🟠 weak) —
   the analyst tells you how much to trust each claim.
2. **Confound discipline** — before/after verdicts require the checklist; no
   checklist, no verdict.
3. **Honest limits** — a whole playbook about what wearables *cannot* measure
   (nutrition, mood causes, muscle vs fat, blood biomarkers...), so "no
   detectable effect" and "not measurable" are never confused.
4. **Data traps fixed, with receipts** — every fix is reported with its
   inflation number (on the author's data: naive step sums were +73%,
   flights +82%, six sleep sources merged 44,510 segments into 2,936).
5. **Numbers from computation, never from the model's memory** — an iron law
   in the skill itself.

## Install

```bash
git clone https://github.com/FlewolfXY/apple-health-analyst
cp -r apple-health-analyst ~/.cursor/skills/apple-health-analyst
```

## Quickstart

1. iPhone → Health app → profile picture → **Export All Health Data** →
   AirDrop the zip to your Mac and unzip it.
2. Open the folder in Cursor and say: **"analyze my apple health export"**.
3. The agent does the rest. Everything below is optional reading.

```bash
# What the agent runs under the hood:
python3 scripts/inventory.py export.xml --json analysis/inventory.json
python3 scripts/build_daily.py export.xml --out analysis/
```

## Privacy

Everything runs **locally**. The scripts are stdlib-only Python with zero
network access; only statistical aggregates (medians, correlations, trends)
enter the chat context. The bundled `.gitignore` refuses `*.xml` and
`analysis/` so your data can't be committed by accident.

## Roadmap

- Hearing-dose audit (NIOSH-style weekly dose from headphone exposure)
- Cycle-phase overlays for all recovery metrics
- GPX workout-route footprint maps
- Multi-export diffing ("what changed since last month's export?")
- Synthetic demo export for trying the skill without your own data

## Disclaimer

Not medical advice. Consumer sensors estimate — this skill reads trends, not
diagnoses. For anything alarming, see a doctor.

---

# 中文说明

**把 Cursor 变成你的私人健康数据分析师的 agent skill。**
喂给它你的 Apple Health 导出,得到一个可以随时追问的常驻分析师——而不是一份一次性报告。

## 为什么做这个

你的 Apple Watch 多年来默默记录了几百万条身体数据。市面上碰这份导出的工具,要么
把一堆图表倒在你脸上,要么悄悄算错数(步数双重计数、多个 App 叠出"每晚 22 小时
睡眠")。它们都是报告生成器,而报告只能回答写它时想到的问题——你的身体下周就会
提出新的。

这个 skill 走另一条路:一次性 onboarding 之后,agent 对你的数据保持一场
**持续的、诚实的调查**。你用自然语言提问,它用当场计算回答,每个结论带证据等级;
当数据真的答不了时,它会诚实地说"这个测不出,能测的仪器是 XX"。

## 它做什么

- **Onboarding**:流式解析 `export.xml`(GB 级安全,纯标准库,约 1 分钟),把你
  的数据画成"技能树",自动修复已知数据陷阱,建成日级清洗宽表,产出第一份报告。
- **报告以双向提问收尾**:从*你自己的*发现里生成的引导问题(复制粘贴即可继续),
  以及数据对*你*的反问——传感器看到身体明显承压却解释不了原因的时期。你的回答
  本身成为数据。
- **持续分析**:睡眠时相/规律性、恢复基线、疾病特征、体能轨迹、活动-睡眠耦合、
  基于步态的力量代理指标——每类问题都有一本写满陷阱的调查手册(playbook)。
- **干预验证**:"我开始做 X 了,有用吗?"必须过混杂检查清单(季节/趋势/窗口污染/
  周期/共变)。窗口太脏时它会拒绝下结论,转而帮你设计一个干净的 n-of-1 实验。
- **记忆**:发现写入只增不改的台账,实验预注册并带评估日期,新会话秒级接上进度。

## 隐私

全部本地运行。脚本是零网络访问的纯标准库 Python,进入对话上下文的只有统计聚合值。
自带的 `.gitignore` 拒绝 `*.xml` 和 `analysis/`,防止健康数据被误提交。

## 免责声明

不构成医疗建议。消费级传感器是估算——这个 skill 读的是趋势,不是诊断。
有任何令人担忧的症状,请就医。

## License

MIT
