# claude-tokens-plugin

A Claude Code plugin that adds a `/tokens:tokens` command to report your complete historical token usage and cost breakdown across all local projects.

## Install

```bash
claude plugin marketplace add PeterCang/claude-tokens-plugin
claude plugin install tokens@claude-tokens-plugin --scope user
```

Then use it in any Claude Code session:

```
/tokens:tokens
```

## Update

```bash
claude plugin update tokens@claude-tokens-plugin
```

This updates both the skill and the bundled `token_stats.py` script.

## Uninstall

```bash
claude plugin uninstall tokens@claude-tokens-plugin
claude plugin marketplace remove claude-tokens-plugin
```

## What it shows

- **Today's usage** — token breakdown by project for the current day, with cost
- **Overview** — active period, projects, sessions, avg session duration & messages
- **Token breakdown** — input / cache_write / cache_read / output with percentages
- **Cost estimate** — actual cost vs hypothetical no-cache cost, daily & per-session averages
- **Cache efficiency** — hit rate and visual bar charts
- **By model** — token counts and cost per model (Sonnet, Opus, Haiku…)
- **Tool call ranking** — which tools (Read, Bash, Edit…) you use most
- **By project** — top 15 projects by token consumption and cost
- **Weekly trend** — week-by-week usage with bar chart
- **By date** — top 20 days by consumption
- **Pricing reference** — full Anthropic pricing table embedded in the script

## Requirements

- Claude Code with session history in `~/.claude/projects/`
- Python 3.9+ (no extra packages needed)

## Notes

- Cost estimates use **Anthropic's official API pricing** (embedded in `token_stats.py`, last updated 2026-04). Update the `PRICING` dict if prices change.
- Non-Anthropic models fall back to Sonnet 4.6 pricing — treat those as rough estimates.
- The script deduplicates retried messages to avoid double-counting.

## License

MIT
