---
title: "Telegram–Claude Code Bridge Using Max Plan"
category: ideas
tags: [ideas, 2026-04-07]
source_reel: "https://www.instagram.com/reel/DWy7e6QE1aj/?igsh=YTEyeThqM215eGVs"
source_platform: instagram
date_added: 2026-04-07
pipeline_run: run/2026-04-07T03-44-16
status: seed
---

# Telegram–Claude Code Bridge Using Max Plan

## The Idea
Ahmed sees a pattern here that could help his own setup: running Claude Code CLI persistently in a Tmux session and controlling it through Telegram, so the Claude Max subscription does the heavy lifting instead of burning API credits. The bridge works by injecting messages directly into the Claude Code text box, which means it's not just a chatbot wrapper — it's a full Claude Code session you can drive remotely. This could slot neatly into his existing brain/body (Claude Code + GSD 2) architecture as a mobile control layer.

## What Sparked It
> "The system works by actually running an instance of ClaudeCode CLI in a Tmux terminal 24-7 so that we can connect to it with Telegram and send it messages that are actually typed directly into the text box of ClaudeCode CLI."
> "Because messaging injects directly into the text box, we can actually have agents message each other."
> "The system also knows how to spin up new agents, so you can spin up new agents and new ClaudeCode sessions directly from Telegram."

## Why This Could Matter
Ahmed already has Claude Code running as the brain of his local stack — adding a Telegram bridge would let him kick off tasks, check on agents, and spin up new sessions from his phone without being at the desktop. It also keeps costs predictable by staying on the Max plan rather than metered API calls.

## Possible Next Steps
- [ ] Check if the project/install guide referenced in the video is publicly findable (search for "OpenClaw Claude Code Telegram" or the creator's community)
- [ ] Prototype the core: a Tmux session running `claude` + a simple script that sends keystrokes to it via `tmux send-keys`
- [ ] Question to answer first: does this play nicely with the existing GSD 2 headless setup, or would they conflict on the same session?

## Raw Note
> see if this helps

---
*Idea captured by claude-knowledge-pipeline | 2026-04-07*
