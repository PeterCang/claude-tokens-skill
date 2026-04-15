#!/usr/bin/env python3
"""
统计 Claude Code 本地所有项目历史消耗的 Token 总量
扫描 ~/.claude/projects/ 下所有 .jsonl 会话文件
"""

import sys; sys.stdout.reconfigure(encoding='utf-8')
import json
import pathlib
from collections import defaultdict
from datetime import datetime, timezone

# ── 官方定价表（USD / 百万 token，来源：anthropic.com/pricing，2026-04）──
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

def readable_num(n):
    if n >= 1_0000_0000: return f"约 {n/1_0000_0000:.1f} 亿"
    if n >= 1000_0000:   return f"约 {n/1000_0000:.1f} 千万"
    if n >= 100_0000:    return f"约 {n/100_0000:.1f} 百万"
    return f"约 {n/1_0000:.1f} 万"

def cjk_len(s: str) -> int:
    """计算字符串的显示宽度（中文字符占 2 列）"""
    w = 0
    for c in s:
        cp = ord(c)
        if (0x1100 <= cp <= 0x115F or 0x2E80 <= cp <= 0x303E or
                0x3040 <= cp <= 0x33FF or 0x3400 <= cp <= 0x4DBF or
                0x4E00 <= cp <= 0xA4CF or 0xA960 <= cp <= 0xA97F or
                0xAC00 <= cp <= 0xD7FF or 0xF900 <= cp <= 0xFAFF or
                0xFE10 <= cp <= 0xFE1F or 0xFE30 <= cp <= 0xFE6F or
                0xFF01 <= cp <= 0xFF60 or 0xFFE0 <= cp <= 0xFFE6 or
                0x1B000 <= cp <= 0x1B77F or 0x1F300 <= cp <= 0x1FAFF or
                0x20000 <= cp <= 0x3FFFD):
            w += 2
        else:
            w += 1
    return w

def ljust_cjk(s: str, width: int) -> str:
    """按显示宽度左对齐填充空格"""
    pad = width - cjk_len(s)
    return s + " " * max(pad, 0)

def bar(ratio, width=20):
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled)

W = 72

def section(title):
    print(f"\n  {'─'*3} {title} {'─'*(W-6-len(title))}")

def main():
    claude_dir = pathlib.Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        print("未找到 ~/.claude/projects/ 目录"); return

    total      = defaultdict(int)
    by_model   = defaultdict(lambda: defaultdict(int))
    by_project = defaultdict(lambda: defaultdict(int))
    by_date    = defaultdict(lambda: defaultdict(int))
    by_week    = defaultdict(lambda: defaultdict(int))
    tool_calls = defaultdict(int)
    by_date_project = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))  # date->proj->key

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
                    total[key]                        += val
                    by_model[model][key]              += val
                    by_project[project_name][key]     += val
                    by_date[date][key]                += val
                    by_week[week][key]                += val
                    by_date_project[date][project_name][key] += val

    # ── 派生指标 ──────────────────────────────────────────────────
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
    # 假设无缓存时的费用（所有 cache_cr + cache_rd 都按 input 价计）
    nocache_cost = sum(
        calc_cost(d["input_tokens"] + d["cache_creation_input_tokens"] + d["cache_read_input_tokens"],
                  0, 0, d["output_tokens"], model)
        for model, d in by_model.items()
    )
    cache_saving = nocache_cost - total_cost
    cache_hit_rate = cache_rd / (cache_cr + cache_rd) if (cache_cr + cache_rd) > 0 else 0

    active_days = len([d for d in all_dates if d != "unknown"])
    avg_daily_cost = total_cost / active_days if active_days else 0
    avg_session_dur = sum(session_durations) / len(session_durations) if session_durations else 0
    avg_session_msgs = sum(session_msg_counts) / len(session_msg_counts) if session_msg_counts else 0
    first_date = min(d for d in all_dates if d != "unknown") if all_dates else "N/A"
    last_date  = max(d for d in all_dates if d != "unknown") if all_dates else "N/A"

    # ════════════════════════════════════════════════════════════════
    print("\n" + "═" * W)
    print("    Claude Code 历史 Token 消耗统计")
    print("═" * W)

    # ── 0. 今日统计 ───────────────────────────────────────────────
    today = datetime.now().strftime("%Y-%m-%d")
    today_d = by_date.get(today, defaultdict(int))
    today_inp  = today_d["input_tokens"]
    today_ccr  = today_d["cache_creation_input_tokens"]
    today_crd  = today_d["cache_read_input_tokens"]
    today_out  = today_d["output_tokens"]
    today_tot  = today_inp + today_ccr + today_crd + today_out
    today_cost = calc_cost(today_inp, today_ccr, today_crd, today_out, "claude-sonnet-4-6")

    section(f"今日消耗  {today}")
    PL = 26
    print(f"  {ljust_cjk('输入 (input)', PL)} {today_inp:>14,}")
    print(f"  {ljust_cjk('缓存写入 (cache_write)', PL)} {today_ccr:>14,}")
    print(f"  {ljust_cjk('缓存命中 (cache_read)', PL)} {today_crd:>14,}")
    print(f"  {ljust_cjk('输出 (output)', PL)} {today_out:>14,}")
    print(f"  {'─'*52}")
    print(f"  {ljust_cjk('合计', PL)} {today_tot:>14,}  {readable_num(today_tot)}")
    print(f"  {ljust_cjk('合计费用', PL)} {'$'+f'{today_cost:.2f}':>14}  ≈ ¥{today_cost*7.25:,.0f} CNY")

    # 今日按项目明细
    today_projs = by_date_project.get(today, {})
    if today_projs:
        print(f"\n  {'项目':<36} {'输入':>9} {'缓存写':>9} {'缓存读':>9} {'输出':>7}  {'费用':>8}")
        print(f"  {'─'*80}")
        def tp_total(d):
            return sum(d[k] for k in ("input_tokens","output_tokens",
                                       "cache_creation_input_tokens","cache_read_input_tokens"))
        for proj, d in sorted(today_projs.items(), key=lambda x: tp_total(x[1]), reverse=True):
            name = (proj[:34]+"..") if len(proj)>36 else proj
            i  = d["input_tokens"]
            cr = d["cache_creation_input_tokens"]
            rd = d["cache_read_input_tokens"]
            o  = d["output_tokens"]
            c  = calc_cost(i, cr, rd, o, "claude-sonnet-4-6")
            print(f"  {name:<36} {i:>9,} {cr:>9,} {rd:>9,} {o:>7,}  ${c:>7.2f}")

    # ── 1. 总览 ───────────────────────────────────────────────────
    section("总览")
    L = 18
    print(f"  {ljust_cjk('使用周期', L)} {first_date}  →  {last_date}  （{active_days} 个活跃日）")
    print(f"  {ljust_cjk('扫描项目 / 会话', L)} {project_count} 个项目   {session_count} 个会话")
    print(f"  {ljust_cjk('平均会话时长', L)} {avg_session_dur:.0f} 分钟")
    print(f"  {ljust_cjk('平均每会话消息数', L)} {avg_session_msgs:.0f} 条")

    # ── 2. Token 明细 ─────────────────────────────────────────────
    section("Token 明细")
    rows = [
        ("输入 (input)",          input_t,  "标准输入，base 价计费"),
        ("缓存写入 (cache_write)", cache_cr, "首次写入缓存，1.25x base 价"),
        ("缓存命中 (cache_read)",  cache_rd, "命中缓存，0.1x base 价（最省钱）"),
        ("输出 (output)",          output_t, "输出，约 5x input 价"),
    ]
    TL = 26
    for label, val, note in rows:
        pct = val / grand * 100 if grand else 0
        print(f"  {ljust_cjk(label, TL)} {val:>14,}  {pct:4.1f}%  {note}")
    print(f"  {'─'*68}")
    print(f"  {ljust_cjk('合计', TL)} {grand:>14,}        {readable_num(grand)}")

    # ── 3. 费用估算 ───────────────────────────────────────────────
    section("费用估算（按 Anthropic 官方定价）")
    FL = 16
    cost_rows = [
        ("实际费用",       f"${total_cost:>10.2f}",    f"≈ ¥{total_cost*7.25:,.0f} CNY"),
        ("假设无缓存费用",  f"${nocache_cost:>10.2f}",  f"≈ ¥{nocache_cost*7.25:,.0f} CNY"),
        ("缓存节省费用",   f"${cache_saving:>10.2f}",  f"≈ ¥{cache_saving*7.25:,.0f} CNY  🎉"),
        ("平均每活跃日费用", f"${avg_daily_cost:>10.2f}", f"≈ ¥{avg_daily_cost*7.25:,.0f} CNY"),
    ]
    if session_count:
        cost_rows.append(("平均每会话费用", f"${total_cost/session_count:>10.2f}", ""))
    for label, usd, cny in cost_rows:
        print(f"  {ljust_cjk(label, FL)} {usd}  {cny}")

    # ── 4. 缓存效率 ───────────────────────────────────────────────
    section("缓存效率")
    print(f"  缓存命中率   {cache_hit_rate*100:5.1f}%  {bar(cache_hit_rate)}")
    cache_ratio = (cache_cr + cache_rd) / grand if grand else 0
    print(f"  缓存占总量   {cache_ratio*100:5.1f}%  {bar(cache_ratio)}")
    output_ratio = output_t / grand if grand else 0
    print(f"  输出占总量   {output_ratio*100:5.1f}%  {bar(output_ratio)}")

    # ── 5. 按模型分类 ─────────────────────────────────────────────
    section("按模型分类")
    print(f"  {'模型':<24} {'输入':>10} {'缓存写':>10} {'缓存读':>10} {'输出':>8}  {'费用(USD)':>10}")
    print(f"  {'─'*68}")
    model_costs = []
    for model, d in by_model.items():
        cost = calc_cost(d["input_tokens"], d["cache_creation_input_tokens"],
                         d["cache_read_input_tokens"], d["output_tokens"], model)
        model_costs.append((model, d, cost))
    for model, d, cost in sorted(model_costs, key=lambda x: -x[2]):
        name = (model[:22] + "..") if len(model) > 24 else model
        print(f"  {name:<24} {d['input_tokens']:>10,} {d['cache_creation_input_tokens']:>10,} "
              f"{d['cache_read_input_tokens']:>10,} {d['output_tokens']:>8,}  ${cost:>9.2f}")

    # ── 6. 工具调用排行 ───────────────────────────────────────────
    section("工具调用排行 (Top 12)")
    top_tools = sorted(tool_calls.items(), key=lambda x: -x[1])[:12]
    total_tool_calls = sum(tool_calls.values())
    print(f"  总工具调用次数: {total_tool_calls:,}")
    print()
    max_calls = top_tools[0][1] if top_tools else 1
    for tool, count in top_tools:
        pct = count / total_tool_calls * 100
        b = bar(count / max_calls, 16)
        print(f"  {tool:<28} {count:>6,}  {pct:4.1f}%  {b}")

    # ── 7. 按项目排行 ─────────────────────────────────────────────
    section("按项目消耗排行 (Top 15)")
    print(f"  {'项目':<36} {'合计 Token':>12}  {'费用(USD)':>10}  {'占比':>5}")
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
        print(f"  {name:<36} {tot:>12,}  ${cost:>9.2f}  {pct:4.1f}%")

    # ── 8. 按周趋势 ───────────────────────────────────────────────
    section("按周消耗趋势")
    print(f"  {'周':<12} {'Token 合计':>12}  {'费用(USD)':>10}  趋势")
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
        b    = bar(tot / max_week, 18)
        print(f"  {week:<12} {tot:>12,}  ${cost:>9.2f}  {b}")

    # ── 9. 按日期排行 ─────────────────────────────────────────────
    section("按日期消耗排行 (Top 20)")
    print(f"  {'日期':<12} {'Token 合计':>12}  {'费用(USD)':>10}  {'占比':>5}")
    print(f"  {'─'*68}")
    def day_total(d):
        return sum(d[k] for k in ("input_tokens","output_tokens",
                                   "cache_creation_input_tokens","cache_read_input_tokens"))
    for date, d in sorted(by_date.items(), key=lambda x: day_total(x[1]), reverse=True)[:20]:
        tot  = day_total(d)
        cost = calc_cost(d["input_tokens"], d["cache_creation_input_tokens"],
                         d["cache_read_input_tokens"], d["output_tokens"], "claude-sonnet-4-6")
        pct  = tot / grand * 100 if grand else 0
        print(f"  {date:<12} {tot:>12,}  ${cost:>9.2f}  {pct:4.1f}%")

    # ── 10. 定价参考 ──────────────────────────────────────────────
    section("定价参考（来源：anthropic.com/pricing，2026-04，单位 $/MTok）")
    print(f"  {'模型':<22} {'input':>7} {'cache_write':>12} {'cache_read':>11} {'output':>8}")
    print(f"  {'─'*64}")
    for key, (pi, pcr, prd, po) in PRICING.items():
        if key == "_default": continue
        print(f"  {key:<22} {pi:>7.2f} {pcr:>12.2f} {prd:>11.2f} {po:>8.2f}")

    print("\n" + "═" * W)
    print(f"  统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == "__main__":
    main()
