---
name: tokens
description: Count all historical Claude Code token usage across all local projects, broken down by model, project, date, and week. Includes cost estimation based on official Anthropic pricing.
---

# Token Stats

## Step 1 — Detect Python

```bash
python --version 2>/dev/null || python3 --version 2>/dev/null || echo "PYTHON_NOT_FOUND"
```

If the output is `PYTHON_NOT_FOUND`, Python is not installed. Tell the user:

> Python is required but not found on your system. Please install it:
> - **Windows**: `winget install Python.Python.3` or https://www.python.org/downloads/ (check "Add Python to PATH")
> - **macOS**: `brew install python3` or https://www.python.org/downloads/
> - **Linux**: `sudo apt install python3` / `sudo yum install python3`
>
> After installing Python, run `/tokens:tokens` again.

Then stop — do not continue.

## Step 2 — Locate and run the bundled script

```bash
SCRIPT=$(find "$HOME/.claude/plugins/cache" -name "token_stats.py" 2>/dev/null | head -1)
if [ -z "$SCRIPT" ]; then
  echo "ERROR: token_stats.py not found. Try: claude plugin update tokens@claude-tokens-plugin"
  exit 1
fi
python "$SCRIPT" 2>/dev/null || python3 "$SCRIPT"
```

Display the output directly without additional explanation.
