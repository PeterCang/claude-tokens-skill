#!/usr/bin/env python3
"""
Claude Code Token Stats
Scans all ~/.claude/projects/ session files and reports historical token usage.
"""

import sys; sys.stdout.reconfigure(encoding='utf-8')
import json
import pathlib
from collections import defaultdict
from datetime import datetime

# ── Official Anthropic pricing (USD / MTok, source: anthropic.com/pricing, 2026-04) ──
# (input, cache_write_5m, cache_read, output)
PRICING = {
    "claude-opus-4-6":   (5.00,  6.25,  0.50, 25.00),
    "claude-opus-4-5":   (5.00,  6.25,  0.50, 25.00),
    "claude-opus-4-1":   (15.00, 18.75, 1.50, 75.00),
    "claude-opus-4":     (15.00, 18.75, 1.50, 75.00),
    "claude-sonnet-4-6": (3.00,  3.75,  0.30, 15.00),
    "claude-sonnet-4-5": (3.00,  3.75,  0.30, 15.00),
    "claude-sonnet-4":   (3.00,  3.75,  0.30, 15.00),
    "claude-sonnet-3-7": (3.00,  3.75,  0.30, 15.00),
    "claude-haiku-4-5":  (1.00,  1.25,  0.10,  5.00),
    "claude-haiku-3-5":  (0.80,  1.00,  0.08,  4.00),
    "claude-haiku-3":    (0.25,  0.30,  0.03,  1.25),
    "claude-opus-3":     (15.00, 18.75, 1.50, 75.00),
    "_default":          (3.00,  3.75,  0.30, 15.00),
}

def get_price(model: str):
    m = model.lower().replace("_", "-")
    for key, price in PRICING.items():
        if key == "_default": continue
        if m.startswith(key) or key in m:
            return price
    return PRICING["_default"]

def calc_cost(inp, ccr, crd, out, model):
    p_in, p_ccr, p_crd, p_out = get_price(model)
    return (inp * p_in + ccr * p_ccr + crd * p_crd + out * p_out) / 1_000_000

def parse_jsonl(path):
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line: continue
        try: yield json.loads(line)
        except: continue

def cjk_len(s: str) -> int:
    w = 0
    for c in s:
        cp = ord(c)
        if (0x1100 <= cp <= 0x115F or 0x2E80 <= cp <= 0x303E or
                0x3040 <= cp <= 0x33FF or 0x3400 <= cp <= 0x4DBF or
                0x4E00 <= cp <= 0xA4CF or 0xAC00 <= cp <= 0xD7FF or
                0xF900 <= cp <= 0xFAFF or 0xFF01 <= cp <= 0xFF60 or
                0xFFE0 <= cp <= 0xFFE6):
            w += 2
        else:
            w += 1
    return w

def ljust_cjk(s: str, width: int) -> str:
    return s + " " * max(width - cjk_len(s), 0)

def readable_num(n):
    if n >= 100_000_000: return f"~{n/100_000_000:.1f}B"
    if n >= 10_000_000:  return f"~{n/1_000_000:.0f}M"
    if n >= 1_000_000:   return f"~{n/1_000_000:.1f}M"
    return f"~{n/1_000:.0f}K"

def bar(ratio, width=18):
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled)

W = 72

def section(title):
    print(f"\n  {'─'*3} {title} {'─'*(W-6-len(title))}")

def main():
    claude_dir = pathlib.Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        print("~/.claude/projects/ not found"); return

    total      = defaultdict(int)
    by_model   = defaultdict(lambda: defaultdict(int))
    by_project = defaultdict(lambda: defaultdict(int))
    by_date    = defaultdict(lambda: defaultdict(int))
    by_week    = defaultdict(lambda: defaultdict(int))
    tool_calls = defaultdict(int)

    session_count = 0
    project_count = 0
    seen_sessions = set()
    session_durations = []
    session_msg_counts = []
    all_dates = set()

    for project_dir in sorted(claude_dir.iterdir()):
        if not project_dir.is_dir(): continue
        project_name = project_dir.name
        project_count += 1

        for jsonl_file in project_dir.glob("*.jsonl"):
            session_id = jsonl_file.stem
            if session_id in seen_sessions: continue

            msg_usage, msg_date, msg_model = {}, {}, {}
            session_timestamps = []
            session_msg_count = 0

            for obj in parse_jsonl(jsonl_file):
                ts = obj.get("timestamp", "")
                if ts and obj.get("type") in ("user", "assistant"):
                    session_timestamps.append(ts)
                    session_msg_count += 1

                if obj.get("type") == "assistant":
                    msg = obj.get("message", {})
                    usage = msg.get("usage")
                    if not usage: continue
                    uuid  = obj.get("uuid", jsonl_file.stem + str(len(msg_usage)))
                    model = msg.get("model", "_default")
                    msg_usage[uuid] = usage
                    msg_date[uuid]  = ts[:10] if ts else "unknown"
                    msg_model[uuid] = model
                    for c in msg.get("content", []):
                        if isinstance(c, dict) and c.get("type") == "tool_use":
                            tool_calls[c.get("name", "unknown")] += 1

            if msg_usage:
                seen_sessions.add(session_id)
                session_count += 1
                session_msg_counts.append(session_msg_count)
                if len(session_timestamps) >= 2:
                    session_timestamps.sort()
                    try:
                        t0 = datetime.fromisoformat(session_timestamps[0].replace("Z", "+00:00"))
                        t1 = datetime.fromisoformat(session_timestamps[-1].replace("Z", "+00:00"))
                        session_durations.append((t1 - t0).total_seconds() / 60)
                    except: pass

            for uuid, usage in msg_usage.items():
                date  = msg_date.get(uuid, "unknown")
                model = msg_model.get(uuid, "_default")
                all_dates.add(date)
                try:
                    dt = datetime.strptime(date, "%Y-%m-%d")
                    week = dt.strftime("%Y-W%W")
                except: week = "unknown"
                for key in ("input_tokens", "output_tokens",
                            "cache_creation_input_tokens", "cache_read_input_tokens"):
                    val = usage.get(key, 0) or 0
                    total[key]                    += val
                    by_model[model][key]          += val
                    by_project[project_name][key] += val
                    by_date[date][key]            += val
                    by_week[week][key]            += val

    input_t  = total["input_tokens"]
    output_t = total["output_tokens"]
    cache_cr = total["cache_creation_input_tokens"]
    cache_rd = total["cache_read_input_tokens"]
    grand    = input_t + output_t + cache_cr + cache_rd

    total_cost = sum(
        calc_cost(d["input_tokens"], d["cache_creation_input_tokens"],
                  d["cache_read_input_tokens"], d["output_tokens"], model)
        for model, d in by_model.items()
    )
    nocache_cost = sum(
        calc_cost(d["input_tokens"] + d["cache_creation_input_tokens"] + d["cache_read_input_tokens"],
                  0, 0, d["output_tokens"], model)
        for model, d in by_model.items()
    )
    cache_saving   = nocache_cost - total_cost
    cache_hit_rate = cache_rd / (cache_cr + cache_rd) if (cache_cr + cache_rd) > 0 else 0
    active_days    = len([d for d in all_dates if d != "unknown"])
    avg_daily_cost = total_cost / active_days if active_days else 0
    avg_session_dur  = sum(session_durations) / len(session_durations) if session_durations else 0
    avg_session_msgs = sum(session_msg_counts) / len(session_msg_counts) if session_msg_counts else 0
    first_date = min(d for d in all_dates if d != "unknown") if all_dates else "N/A"
    last_date  = max(d for d in all_dates if d != "unknown") if all_dates else "N/A"

    print("\n" + "═" * W)
    print("    Claude Code Token Usage Statistics")
    print("═" * W)

    section("Overview")
    L = 22
    print(f"  {ljust_cjk('Active period', L)} {first_date}  →  {last_date}  ({active_days} active days)")
    print(f"  {ljust_cjk('Projects / Sessions', L)} {project_count} projects   {session_count} sessions")
    print(f"  {ljust_cjk('Avg session duration', L)} {avg_session_dur:.0f} min")
    print(f"  {ljust_cjk('Avg messages/session', L)} {avg_session_msgs:.0f}")

    section("Token Breakdown")
    rows = [
        ("Input",        input_t,  "Standard input, billed at base rate"),
        ("Cache write",  cache_cr, "First write to cache, 1.25x base rate"),
        ("Cache read",   cache_rd, "Cache hit, 0.1x base rate (cheapest)"),
        ("Output",       output_t, "Output tokens, ~5x input rate"),
    ]
    TL = 14
    for label, val, note in rows:
        pct = val / grand * 100 if grand else 0
        print(f"  {ljust_cjk(label, TL)} {val:>16,}  {pct:4.1f}%  {note}")
    print(f"  {'─'*68}")
    print(f"  {ljust_cjk('Total', TL)} {grand:>16,}        {readable_num(grand)}")

    section("Cost Estimate (Anthropic official pricing)")
    FL = 26
    cost_rows = [
        ("Actual cost",          f"${total_cost:>10.2f}",    f"≈ ¥{total_cost*7.25:,.0f} CNY"),
        ("Without cache (est.)", f"${nocache_cost:>10.2f}",  f"≈ ¥{nocache_cost*7.25:,.0f} CNY"),
        ("Cache savings",        f"${cache_saving:>10.2f}",  f"≈ ¥{cache_saving*7.25:,.0f} CNY"),
        ("Avg cost/active day",  f"${avg_daily_cost:>10.2f}", f"≈ ¥{avg_daily_cost*7.25:,.0f} CNY"),
    ]
    if session_count:
        cost_rows.append(("Avg cost/session", f"${total_cost/session_count:>10.2f}", ""))
    for label, usd, cny in cost_rows:
        print(f"  {ljust_cjk(label, FL)} {usd}  {cny}")

    section("Cache Efficiency")
    print(f"  Cache hit rate   {cache_hit_rate*100:5.1f}%  {bar(cache_hit_rate)}")
    cache_ratio = (cache_cr + cache_rd) / grand if grand else 0
    print(f"  Cache % of total {cache_ratio*100:5.1f}%  {bar(cache_ratio)}")
    output_ratio = output_t / grand if grand else 0
    print(f"  Output % of total{output_ratio*100:5.1f}%  {bar(output_ratio)}")

    section("By Model")
    print(f"  {'Model':<24} {'Input':>10} {'CacheWr':>10} {'CacheRd':>10} {'Output':>8}  {'Cost(USD)':>10}")
    print(f"  {'─'*68}")
    model_costs = [(m, d, calc_cost(d["input_tokens"], d["cache_creation_input_tokens"],
                                     d["cache_read_input_tokens"], d["output_tokens"], m))
                   for m, d in by_model.items()]
    for model, d, cost in sorted(model_costs, key=lambda x: -x[2]):
        name = (model[:22] + "..") if len(model) > 24 else model
        print(f"  {name:<24} {d['input_tokens']:>10,} {d['cache_creation_input_tokens']:>10,} "
              f"{d['cache_read_input_tokens']:>10,} {d['output_tokens']:>8,}  ${cost:>9.2f}")

    section("Tool Call Ranking (Top 12)")
    top_tools = sorted(tool_calls.items(), key=lambda x: -x[1])[:12]
    total_tool_calls = sum(tool_calls.values())
    print(f"  Total tool calls: {total_tool_calls:,}\n")
    max_calls = top_tools[0][1] if top_tools else 1
    for tool, count in top_tools:
        pct = count / total_tool_calls * 100
        print(f"  {tool:<28} {count:>6,}  {pct:4.1f}%  {bar(count/max_calls, 16)}")

    section("By Project (Top 15)")
    print(f"  {'Project':<36} {'Total Tokens':>13}  {'Cost(USD)':>10}  {'Share':>5}")
    print(f"  {'─'*68}")
    def proj_total(d):
        return sum(d[k] for k in ("input_tokens","output_tokens",
                                   "cache_creation_input_tokens","cache_read_input_tokens"))
    for proj, d in sorted(by_project.items(), key=lambda x: proj_total(x[1]), reverse=True)[:15]:
        name = (proj[:34]+"..") if len(proj)>36 else proj
        tot  = proj_total(d)
        cost = calc_cost(d["input_tokens"], d["cache_creation_input_tokens"],
                         d["cache_read_input_tokens"], d["output_tokens"], "claude-sonnet-4-6")
        pct  = tot / grand * 100 if grand else 0
        print(f"  {name:<36} {tot:>13,}  ${cost:>9.2f}  {pct:4.1f}%")

    section("Weekly Trend")
    print(f"  {'Week':<12} {'Total Tokens':>13}  {'Cost(USD)':>10}  Trend")
    print(f"  {'─'*68}")
    week_totals = {w: sum(d[k] for k in ("input_tokens","output_tokens",
                          "cache_creation_input_tokens","cache_read_input_tokens"))
                   for w, d in by_week.items() if w != "unknown"}
    max_week = max(week_totals.values()) if week_totals else 1
    for week in sorted(week_totals.keys()):
        tot  = week_totals[week]
        d    = by_week[week]
        cost = calc_cost(d["input_tokens"], d["cache_creation_input_tokens"],
                         d["cache_read_input_tokens"], d["output_tokens"], "claude-sonnet-4-6")
        print(f"  {week:<12} {tot:>13,}  ${cost:>9.2f}  {bar(tot/max_week)}")

    section("By Date (Top 20)")
    print(f"  {'Date':<12} {'Total Tokens':>13}  {'Cost(USD)':>10}  {'Share':>5}")
    print(f"  {'─'*68}")
    def day_total(d):
        return sum(d[k] for k in ("input_tokens","output_tokens",
                                   "cache_creation_input_tokens","cache_read_input_tokens"))
    for date, d in sorted(by_date.items(), key=lambda x: day_total(x[1]), reverse=True)[:20]:
        tot  = day_total(d)
        cost = calc_cost(d["input_tokens"], d["cache_creation_input_tokens"],
                         d["cache_read_input_tokens"], d["output_tokens"], "claude-sonnet-4-6")
        pct  = tot / grand * 100 if grand else 0
        print(f"  {date:<12} {tot:>13,}  ${cost:>9.2f}  {pct:4.1f}%")

    section("Pricing Reference (anthropic.com/pricing, 2026-04, USD/MTok)")
    print(f"  {'Model':<22} {'input':>7} {'cache_write':>12} {'cache_read':>11} {'output':>8}")
    print(f"  {'─'*64}")
    for key, (pi, pcr, prd, po) in PRICING.items():
        if key == "_default": continue
        print(f"  {key:<22} {pi:>7.2f} {pcr:>12.2f} {prd:>11.2f} {po:>8.2f}")

    print("\n" + "═" * W)
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == "__main__":
    main()
