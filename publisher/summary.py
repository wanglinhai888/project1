"""每日价格变化摘要：把 today.json 的 changes / summary 渲染为可发布文本。

输入: today.json（crawler 已含 changes 与 summary，无需重新计算 diff）
输出: 纯文本 / Markdown，供公众号、Telegram、邮件等渠道复用。

设计原则（Input -> Calculate -> Result，可脱离 UI 单独测试）：
    build_summary(today)  ->  dict(title, date, text, markdown, meta)
"""
import json
from pathlib import Path

from crawler.config import DATA_FILES


def _fmt_price(value, currency):
    if value is None:
        return "-"
    sym = "$" if currency == "USD" else "¥"
    if float(value) == 0:
        return f"{sym}0"
    return f"{sym}{float(value):.2f}"


def build_summary(today):
    """根据 today.json 生成发布摘要，返回可序列化 dict。"""
    date = today.get("date", "")
    summary = today.get("summary", {}) or {}
    changes = today.get("changes", []) or []

    total = summary.get("total_models", 0)
    providers = summary.get("providers", 0)
    up = summary.get("price_up", 0)
    down = summary.get("price_down", 0)
    new = summary.get("new_models", 0)

    ups = [c for c in changes if c.get("type") == "price_up"]
    downs = [c for c in changes if c.get("type") == "price_down"]
    news = [c for c in changes if c.get("type") == "new_model"]

    title = f"📊 AI 大模型价格日报（{date}）"
    head = (
        f"今日共追踪 {total} 个模型，覆盖 {providers} 家厂商。\n"
        f"🔺 涨价 {up} 个　🔻 降价 {down} 个　🆕 新模型 {new} 个"
    )

    lines = [head, ""]
    md_lines = [f"# {title}", "", head, ""]

    def section(name, items):
        if not items:
            return
        lines.append(f"【{name}】")
        md_lines.append(f"## {name}")
        md_lines.append("")
        for c in items:
            cur = c.get("currency", "USD")
            if c.get("type") == "new_model":
                txt = (
                    f"• {c['provider']} {c['model']}："
                    f"输入 {_fmt_price(c.get('new_input'), cur)} / "
                    f"输出 {_fmt_price(c.get('new_output'), cur)}"
                )
                md = (
                    f"- **{c['provider']} {c['model']}**："
                    f"输入 {_fmt_price(c.get('new_input'), cur)} / "
                    f"输出 {_fmt_price(c.get('new_output'), cur)}"
                )
            else:
                txt = f"• {c['provider']} {c['model']}：{c.get('change', '')}　{c.get('detail', '')}"
                md = (
                    f"- {c['provider']} {c['model']}："
                    f"**{c.get('change', '')}**　{c.get('detail', '')}"
                )
            lines.append(txt)
            md_lines.append(md)
        lines.append("")
        md_lines.append("")

    section("涨价", ups)
    section("降价", downs)
    section("新模型上线", news)

    if not changes:
        lines.append("今日价格无变动。")
        md_lines.append("今日价格无变动。")

    return {
        "title": title,
        "date": date,
        "text": "\n".join(lines).strip(),
        "markdown": "\n".join(md_lines).strip(),
        "meta": summary,
    }


def load_today(path=None):
    """读取 today.json（默认用 crawler.config 中配置的正式路径）。"""
    path = Path(path) if path else DATA_FILES["today"]
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
