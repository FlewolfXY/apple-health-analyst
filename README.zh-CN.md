# apple-health-analyst

[English](README.md) | [简体中文](README.zh-CN.md)

一个 Cursor-first、但不绑定 Cursor 的 Apple Health 分析工作流。

它会把 `export.xml` 变成一个本地的、可持续追问的健康数据分析工作区:
先给你一份报告,然后留下一个能继续查问题的分析师。Cursor 可以把它作为 Skill
加载;Claude Code、Codex 和其他 coding agent 也可以使用同一套脚本和 prompt。

```text
你: 分析我的 Apple Health 导出

Agent:
  - 看你的数据能支持哪些健康分析
  - 修复 Apple Health 常见数据陷阱
  - 建立清洗后的日级宽表
  - 写第一份报告
  - 用报告里的问题引导你继续追问或补充背景
```

## 为什么需要它

Apple Health 导出很丰富,也很难用:

- 原始 `export.xml` 往往有几百万条记录;
- iPhone 和 Apple Watch 会重复写步数、距离、能量消耗;
- 多个睡眠 App 会互相重叠,直接求和可能得到"每晚二十小时睡眠";
- 可穿戴设备能看到身体变了,但看不到你生活里发生了什么。

这个 skill 给 agent 一套可复用的方法:先把数据清洗成可靠的日级表,再按照
playbook 分析睡眠、恢复、活动、体能、步态、听力、周期和干预效果。它不是一个
图表生成器,而是一个本地运行的健康数据分析师。

## 和现有健康 App 有什么不同

大多数健康 App 更像仪表盘:展示本月睡眠、今年趋势、HRV 曲线、运动统计,再给你
一些通用建议。它们擅长呈现数据,但很少真正追问"为什么"。

这个 skill 更像分析师:

- 它会主动挖异常时期、行为变化点和跨指标模式;
- 当传感器只能看到"发生了变化"却看不到原因时,它会反过来问你生活背景;
- 它可以验证你提出的假设,比如"这个习惯到底有没有用";
- 它会承认哪些问题 Apple Health 根本测不出,而不是硬给一个看似聪明的答案;
- 它会留下状态、发现台账和实验计划,下次会话可以接着分析。

所以它不是月报/年报生成器,而是用 AI 帮你挖掘和解读个人健康数据。

## 首次运行会得到什么

首次运行时会生成一个 `analysis/` 目录:

```text
analysis/
  daily.csv          # 清洗后的日级宽表,一日一行
  meta.json          # 已修复的数据陷阱、异常时期、行为变化点
  inventory.json     # 数据覆盖情况和可解锁的分析域
  first_report.md    # 第一份报告,由 agent 在建表后写入
  STATE.md           # 分析师状态记忆
  findings.md        # 只增不改的发现台账
  events.csv         # 用户补充的人生事件/生活背景
  experiments/       # n-of-1 自我实验方案
```

第一份报告不是终点,而是对话入口。它会包括:

- 睡眠、恢复、活动、体能等基线数字;
- 最强的几个发现,每条都带证据等级;
- 数据质量修复记录;
- Apple Health 能回答什么、不能回答什么;
- 可以直接复制粘贴继续问的问题;
- 数据想反问你的地方:身体或行为明显变化,但传感器不知道原因。

## 输出长什么样

inventory 阶段会把原始数据翻译成"能力地图":

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

建表阶段会自动找出值得追问的时期:

```text
NOTABLE PERIODS
  ? 2025-12-23 → 2025-12-28:
    resting heart rate +14 bpm, HRV -6 ms

BEHAVIOR SHIFTS
  ? 2026-05:
    daylight minutes 29 → 154 per day
```

它不会替你编故事。它只会说:这里身体明显承压了,或者某个行为突然变化了。
你那段时间是生病、旅行、换作息、开始新习惯,还是发生了别的事?你的回答会进入
`events.csv`,成为后续分析的上下文。

## 之后可以问什么

```text
我今年睡眠为什么变差了?
我开始用光疗灯之后,入睡时间真的提前了吗?
最近总觉得累,心率和 HRV 能看出来吗?
我的跑步是在真的进步,还是只是 Apple Watch 估算变多了?
帮我设计一个 2 周实验,验证多走路能不能改善睡眠。
这套数据有哪些问题根本测不出来?
```

## 它和普通报告有什么不同

**数字必须现算。** 每个数字都必须来自本地脚本或 `analysis/daily.csv`,不能靠模型记忆。

**结论带证据等级。** 强/中/弱会分开写,避免把"看起来像"说成"已经证明"。

**干预分析必须过混杂清单。** 比如"某个习惯有没有用",必须检查季节、长期趋势、
生病、周期阶段和同期生活变化。

**诚实承认测不出。** 饮食摄入、情绪原因、肌肉还是脂肪、血液指标、很多补剂效果,
Apple Health 本身看不到。测不出时就直说,而不是硬编一个答案。

**冷启动纪律。** 新用户只导入原始数据时,agent 只能用 export 里的信号和用户本轮
亲口补充的信息。看到行为变化就问"发生了什么",不能假装知道原因。

## 安装

Cursor 用户:

```bash
mkdir -p ~/.cursor/skills
git clone https://github.com/FlewolfXY/apple-health-analyst \
  ~/.cursor/skills/apple-health-analyst
```

Claude Code、Codex 或其他 agent 用户,可以把仓库 clone 到任意位置:

```bash
git clone https://github.com/FlewolfXY/apple-health-analyst
```

然后让 agent 读取对应入口:

- Claude Code: `CLAUDE.md`
- Codex / 其他 coding agents: `AGENTS.md`
- 通用可复制 prompt: `prompts/apple-health-analyst.md`

## 使用

1. iPhone 打开"健康" -> 头像 -> **导出所有健康数据**。
2. 把 zip 传到 Mac 并解压。
3. 用 Cursor 打开解压后的文件夹。
4. 对 agent 说: `分析我的 Apple Health 导出`。

skill 会在本地运行。底层脚本大致是:

```bash
python3 ~/.cursor/skills/apple-health-analyst/scripts/onboard.py \
  export.xml --out analysis/
```

脚本只使用 Python 标准库,并且流式解析 XML,GB 级导出也可以处理。

如果不使用 Cursor,也可以用绝对路径直接运行同一个 wrapper:

```bash
python3 /path/to/apple-health-analyst/scripts/onboard.py \
  /path/to/export.xml --out /path/to/export-folder/analysis/
```

## 隐私

原始健康数据留在本机。脚本不需要网络访问。仓库的 `.gitignore` 也会排除
`*.xml`、`*.zip` 和 `analysis/`,避免误提交原始健康数据或生成报告。

## 当前覆盖

- 睡眠时相、时长、规律性、作息惯性
- 静息心率、HRV、呼吸率和恢复基线
- 多信号异常时期,用于回看疑似生病或压力期
- 活动量、Workout 和活动-睡眠关联
- 有记录时的跑步速度、配速、功率和步幅指标
- 有记录时的心率恢复和六分钟步行距离
- 步行速度、上楼速度等步态/移动能力代理指标
- 耳机和环境音量暴露
- 有经期记录时的周期阶段交叉分析
- 干预验证和 n-of-1 自我实验设计

## Roadmap

- 合成 demo 数据和示例报告
- GPX 运动路线地图
- 多次导出对比:这次和上次相比变了什么
- 更细的周期阶段建模
- 按周听力剂量报告
- 不依赖浏览器的报告预览

## 免责声明

这不是医疗建议。消费级可穿戴设备是估算工具,本 skill 分析的是趋势,不是诊断。
如果有令人担忧的症状,请就医。

## License

MIT
