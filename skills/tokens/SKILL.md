---
name: tokens
description: Count all historical Claude Code token usage across all local projects, broken down by model, project, date, and week. Includes cost estimation based on official Anthropic pricing.
---

# Token Stats

First, check if the stats script exists, and if not, download it:

```bash
python -c "import pathlib; p=pathlib.Path.home()/'.claude/token_stats.py'; print('exists') if p.exists() else print('missing')"
```

If the output is "missing", download the script:

```bash
curl -fsSL https://raw.githubusercontent.com/PeterCang/claude-tokens-skill/master/token_stats.py -o "$HOME/.claude/token_stats.py"
```

Then run the stats:

```bash
python "$HOME/.claude/token_stats.py"
```

Display the output directly without additional explanation.
