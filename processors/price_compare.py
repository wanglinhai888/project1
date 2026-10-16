"""价格变化分析：比较今日价格与最近一次历史快照，生成变化报告。

输入: 今日价格列表 + 历史快照列表(history.json)
计算: 相对变化百分比，按阈值判定涨价/降价，识别新模型
输出: changes 列表
"""
from crawler.config import PRICE_CHANGE_THRESHOLD


def _fmt_price(value, currency):
    if value is None:
        return "-"
    sym = "$" if currency == "USD" else "¥"
    if float(value) == 0:
        return f"{sym}0"
    return f"{sym}{float(value):.2f}"


def latest_snapshot_map(history, exclude_date=None):
    """返回最近一天（排除当天）的 {(provider, model): entry}。"""
    dates = sorted({e["date"] for e in history if e.get("date") != exclude_date})
    if not dates:
        return {}
    latest = dates[-1]
    return {(e["provider"], e["model"]): e for e in history if e["date"] == latest}


def compare_prices(today_prices, history, exclude_date=None):
    """对比今日价格与历史，生成变化列表（含新模型）。"""
    changes = []
    old_map = latest_snapshot_map(history, exclude_date)
    if not old_map:
        # 无历史对比（首次上线 / 历史重置），不报新模型，避免全量假新
        return changes

    for p in today_prices:
        key = (p["provider"], p["model"])
        old = old_map.get(key)
        currency = p.get("currency", "USD")

        if old is None:
            changes.append({
                "provider": p["provider"],
                "model": p["model"],
                "type": "new_model",
                "change": None,
                "currency": currency,
                "old_input": None,
                "old_output": None,
                "new_input": p["input_price"],
                "new_output": p["output_price"],
                "detail": "新模型上线",
            })
            continue

        old_in, old_out = old["input_price"], old["output_price"]
        new_in, new_out = p["input_price"], p["output_price"]

        def ratio(old_v, new_v):
            if old_v in (None, 0):
                return 0.0
            return (new_v - old_v) / float(old_v)

        r_in, r_out = ratio(old_in, new_in), ratio(old_out, new_out)
        if abs(r_in) < PRICE_CHANGE_THRESHOLD and abs(r_out) < PRICE_CHANGE_THRESHOLD:
            continue

        change_type = "price_up" if (r_in + r_out) > 0 else "price_down"
        sign = "+" if change_type == "price_up" else "-"
        avg = (abs(r_in) + abs(r_out)) / 2
        changes.append({
            "provider": p["provider"],
            "model": p["model"],
            "type": change_type,
            "change": f"{sign}{avg * 100:.1f}%",
            "currency": currency,
            "old_input": old_in,
            "old_output": old_out,
            "new_input": new_in,
            "new_output": new_out,
            "detail": (
                f"输入价 {_fmt_price(old_in, currency)} → {_fmt_price(new_in, currency)}，"
                f"输出价 {_fmt_price(old_out, currency)} → {_fmt_price(new_out, currency)}"
            ),
        })

    return changes
