# Claude Powers — Knowledge Base

Auto-generated knowledge base about Claude AI capabilities, agent patterns, skills, and prompt engineering. Built by the claude-knowledge-pipeline.

## How to Query

```bash
# Semantic search
python3 ~/projects/claude-pipeline/retrieve.py "multi-agent orchestration" 3

# Feed results to Claude
claude -p "$(python3 ~/projects/claude-pipeline/retrieve.py 'extended thinking' 3)

Based on the above knowledge, answer: how do I use extended thinking effectively?"
```

## Categories

| Folder | Contents |
|--------|----------|
| `agents/` | Claude agent patterns, multi-agent orchestration |
| `skills/` | SKILL.md-format files Claude can load directly |
| `superpowers/` | Advanced Claude capabilities and power-user tips |
| `tools/` | AI tools, MCP servers, integrations |
| `prompts/` | Prompt engineering techniques |
| `updates/` | Model releases, AI news |

## Run the Pipeline

Click the **Claude Pipeline** icon on your desktop, or:
```bash
bash ~/projects/claude-pipeline/run_pipeline.sh
```
