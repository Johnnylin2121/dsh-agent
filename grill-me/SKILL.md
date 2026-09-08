---
name: grill-me
description: >
  需求拷问器：把目标拆成决策树，逐轮提出"当前可答的全部问题"+推荐答案，直到没有隐含假设。
  主动触发词：grill me、拷问我、帮我理清需求、这个方案再盘问一遍、interview me。
  被动触发（模型自动调用）：用户新提出多步骤目标（新项目/新 skill/插件/系统搭建）且关键决策未澄清≥2个；
  或 trading-daily-review 盘后流程要新建交易计划但要素（方向/标的/入场/止损/仓位）未全部明确。
  熔断规则：盘中与复盘执行中不触发；日常问答/小改动/单一查询不触发；
  被动触发只输出 1 轮 ≤5 问（每问附推荐答案），用户明确说"继续"才进入完整多轮模式。
---

## 模式判定（先于一切）

- **完整模式（多轮）**：用户主动点名（"grill me"等触发词）。按下方完整流程执行到底。
- **轻量模式（单轮）**：模型被动触发（匹配 description 中的被动条件）。
  仅一轮：frontier 问题 ≤5 个，每问附推荐答案；结尾给三个选项让用户选——
  「继续深挖（进入多轮）/ 按推荐答案直接开工 / 取消」。
- **交易计划场景**（由 trading-daily-review 盘后交易计划审查调用）：
  决策树范围锁定在 方向/标的/入场逻辑/止损/仓位/时间框架，不扩散到无关分支，先给推荐答案。

## 完整流程（原版）

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled — the questions you can ask *now* without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Each round the user answers reshapes the tree — settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a *later* round, not this one.

Finding *facts* is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it — don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report — ask the rest of the frontier now. The *decisions* are the user's — put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.
