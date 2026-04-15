# claude-tokens-skill

A Claude Code skill (`/tokens`) that scans all local session history and reports your complete token usage and cost breakdown.

## What it shows

- **Overview** — active period, projects, sessions, avg session duration
- **Token breakdown** — input / cache_write / cache_read / output with percentages
- **Cost estimate** — actual cost, hypothetical no-cache cost, savings, daily/session averages
- **Cache efficiency** — hit rate and visual bar charts
- **By model** — token counts and cost per model
- **Tool call ranking** — which tools (Read, Bash, Edit…) you use most
- **By project** — top 15 projects by token consumption
- **Weekly trend** — week-by-week usage with bar chart
- **By date** — top 20 days by consumption
- **Pricing reference** — full Anthropic pricing table embedded in the script

## Requirements

- Python 3.9+
- Claude Code installed with session history in `~/.claude/projects/`

No external Python packages required.

## Installation

### 1. Copy the script

```bash
cp token_stats.py ~/.claude/token_stats.py
```

### 2. Install the skill

```bash
mkdir -p ~/.claude/skills/tokens
cp SKILL.md ~/.claude/skills/tokens/SKILL.md
```

### 3. Done — use it

In any Claude Code session, type:

```
/tokens
```

## Manual usage (without the skill)

```bash
python ~/.claude/token_stats.py
```

## One-liner install

```bash
git clone https://github.com/PeterCang/claude-tokens-skill.git
cd claude-tokens-skill
cp token_stats.py ~/.claude/token_stats.py
mkdir -p ~/.claude/skills/tokens && cp SKILL.md ~/.claude/skills/tokens/SKILL.md
```

## Notes

- Cost estimates use **Anthropic's official API pricing** (embedded in the script, last updated 2026-04). Update the `PRICING` dict in `token_stats.py` if prices change.
- Projects are identified by their directory path encoded as the folder name under `~/.claude/projects/`. The raw folder names are shown as-is.
- The script deduplicates messages to avoid double-counting retried requests.
- Non-Anthropic models (e.g. `qwen3.5-plus`) fall back to Sonnet 4.6 pricing for cost estimation — treat those numbers as rough estimates only.

## License

MIT
