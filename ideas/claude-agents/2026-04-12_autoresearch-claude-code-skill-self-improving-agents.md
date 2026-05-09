---
title: "AutoResearch as a Claude Code Skill: 10 Commands for Autonomous Self-Improving Agents"
category: claude-agents
tags: [claude, claude-agents, autoresearch, karpathy, self-improvement, experiment-loop, skills, optimization]
confidence: high
source_reel: "https://www.instagram.com/reel/DW_wFDyiI0J/?igsh=MWZiY3N1aHI2cHlveA=="
source_platform: instagram
verified_against:
  - "https://github.com/karpathy/autoresearch"
  - "https://github.com/uditgoenka/autoresearch"
date_added: 2026-04-12
claude_applicable: true
pipeline_run: run/2026-04-12T02-30-09
---

# AutoResearch as a Claude Code Skill: 10 Commands for Autonomous Self-Improving Agents

## What Is This
Karpathy's AutoResearch (a ~630-line script that autonomously ran 700 ML experiments overnight, finding an 11% efficiency gain) has been generalized into an installable Claude Code skill. The skill `uditgoenka/autoresearch` ports the core loop — Modify → Verify → Keep/Discard → Repeat — to any measurable domain beyond ML, and packages it as 10 slash commands usable directly in Claude Code sessions.

The key adaptation: instead of optimizing `val_bpb` in a training script, you define any scalar metric (code error count, security finding count, test coverage %, etc.) and constrain the agent's action space. The agent runs the loop autonomously, uses git commits prefixed `experiment:` as its memory, and rolls back failures automatically.

## Why It Matters
The previous AutoResearch note covered the abstract pattern. This is the **concrete, installable implementation**: 10 purpose-built commands you can drop into any Claude Code project today. The meta-application — pointing the skill at Claude's own skills/prompts — creates a compounding improvement loop where the agent gets measurably better at its defined role over time without human involvement between iterations.

## How To Use It

### Install

```bash
# Claude Code (marketplace)
/plugin marketplace add uditgoenka/autoresearch
/plugin install autoresearch@autoresearch

# Manual
cp -r ~/.claude/skills/autoresearch ~/.claude/skills/
cp -r ~/.claude/commands/autoresearch ~/.claude/commands/
```

### The 10 Commands

| Command | What It Does |
|---|---|
| `/autoresearch` | Unbounded optimization loop (main command) |
| `/autoresearch:plan` | Goal-to-config wizard — define metric + action space interactively |
| `/autoresearch:security` | STRIDE/OWASP audit loop |
| `/autoresearch:ship` | Universal deployment workflow |
| `/autoresearch:debug` | Scientific bug-hunting (hypothesis → experiment → result) |
| `/autoresearch:fix` | Error elimination loop |
| `/autoresearch:scenario` | Edge-case explorer |
| `/autoresearch:predict` | 5-expert consensus simulation |
| `/autoresearch:learn` | Documentation freshness loop |
| `/autoresearch:reason` | Adversarial refinement (stress-tests conclusions) |

### The Three Primitives (Required for Any Loop)

```
1. EDITABLE ASSET   — the single file/resource the agent may modify
2. SCALAR METRIC    — one number, unambiguous direction (higher=better or lower=better)
3. TIME-BOXED CYCLE — fixed duration per experiment (makes results directly comparable)
```

### Example: Self-Improving Skill Loop

```markdown
# autoresearch_config.md
EDITABLE ASSET: ~/.claude/skills/my-skill.md
SCALAR METRIC: task_success_rate (read from skill_eval_log.json)
BASELINE: 0.72
DIRECTION: higher is better
CYCLE: evaluate 10 test prompts per iteration

MEMORY: ~/.claude/skills/my-skill-experiments.md (append-only)
GIT: prefix commits with "experiment:" for rollback reference
```

```bash
# In Claude Code
/autoresearch
# Agent will: read config → propose one skill change → apply → evaluate 10 test prompts
# → log result → keep if improved, revert if not → repeat
```

### Core Loop Rules (built into the skill)
1. Loop until interrupted or N iterations reached
2. Read before write — always inspect current state first
3. One atomic change per iteration — no batching
4. Mechanical verification only — no subjective judgment
5. Automatic rollback on failure
6. Prefer simpler solutions when results are equal
7. Git history = memory (`experiment:` prefix commits)
8. Shift to deeper thinking (`/autoresearch:reason`) when stuck 3+ iterations

## Verified Claims
- ✅ Karpathy's autoresearch is a real GitHub project (karpathy/autoresearch) — [github.com/karpathy/autoresearch](https://github.com/karpathy/autoresearch)
- ✅ uditgoenka/autoresearch is a real installable Claude Code skill generalizing the pattern — [github.com/uditgoenka/autoresearch](https://github.com/uditgoenka/autoresearch)
- ✅ Original ran ~700 experiments autonomously with 11% efficiency gain on a well-tuned project — [Fortune](https://fortune.com/2026/03/17/andrej-karpathy-loop-autonomous-ai-agents-future/)
- ⚠️ "OpenClaw" mentioned in video — likely refers to OpenCode (open-source Claude Code alternative); no product called "OpenClaw" verified
- ⚠️ Specific "clinicode.com" skill implementation — unverified, likely a paid wrapper around the open-source uditgoenka/autoresearch skill

## Sources
- [karpathy/autoresearch (GitHub)](https://github.com/karpathy/autoresearch)
- [uditgoenka/autoresearch — Claude Code Skill](https://github.com/uditgoenka/autoresearch)
- [DataCamp AutoResearch Guide](https://www.datacamp.com/tutorial/guide-to-autoresearch)
- [Original Source Reel](https://www.instagram.com/reel/DW_wFDyiI0J/?igsh=MWZiY3N1aHI2cHlveA==)

---
*Auto-generated by claude-knowledge-pipeline | 2026-04-12*
