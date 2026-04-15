---
name: tokens
description: Count all historical Claude Code token usage across all local projects, broken down by model, project, date, and week. Includes cost estimation based on official Anthropic pricing.
---

# Token Stats

## Step 1 — Detect Python

Run this to find a working Python executable:

```bash
python --version 2>/dev/null || python3 --version 2>/dev/null || echo "PYTHON_NOT_FOUND"
```

If the output is `PYTHON_NOT_FOUND`, Python is not installed. Tell the user:

> Python is required but not found on your system. Please install it:
> - **Windows**: https://www.python.org/downloads/ (check "Add Python to PATH" during install), or run `winget install Python.Python.3`
> - **macOS**: `brew install python3` or https://www.python.org/downloads/
> - **Linux**: `sudo apt install python3` / `sudo yum install python3`
>
> After installing Python, run `/tokens:tokens` again.

Then stop — do not continue.

## Step 2 — Detect the correct Python command

Determine which command works: `python` or `python3`. Use whichever returned a version number above. Store it as `PYTHON_CMD`.

## Step 3 — Ensure the stats script is present

```bash
test -f "$HOME/.claude/token_stats.py" && echo "exists" || echo "missing"
```

If "missing", download it:

```bash
curl -fsSL https://raw.githubusercontent.com/PeterCang/claude-tokens-skill/master/token_stats.py -o "$HOME/.claude/token_stats.py"
```

## Step 4 — Run the stats

Use the Python command detected in Step 2:

```bash
python "$HOME/.claude/token_stats.py"
```

or

```bash
python3 "$HOME/.claude/token_stats.py"
```

Display the output directly without additional explanation.
