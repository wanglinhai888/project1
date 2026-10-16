#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEO / GEO 构建脚本（与每日价格更新一起运行）

产物（均写入 website/，由 Cloudflare Pages 直接静态托管）：
  - prices.html       预渲染的实时价格表（无 JS，百度/Google 可直接抓取）
  - promotions.html   预渲染的优惠活动列表
  - tools.html        预渲染的工具指南（含价格/套餐）
  - sitemap.xml       站点地图（每日随数据刷新 lastmod）
  - robots.txt        爬虫协议
  - llms.txt          llmstxt.org 标准，供大模型/Agent 直接读取
  - _headers          Cloudflare Pages / Netlify 跨域头（data & api 允许 CORS）
  - api/prices.json   对外 API：实时价格
  - api/promotions.json  对外 API：优惠活动
  - api/tools.json       对外 API：工具指南

仅使用 Python 标准库，无第三方依赖。
"""
import json
import os
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = HERE

SITE_URL = os.environ.get("SITE_URL", "https://aipriceradar.pages.dev").rstrip("/")
SITE_NAME_ZH = "AI 大模型价格雷达"
SITE_NAME_EN = "AI Model Price Radar"

# ---------------------------------------------------------------------------
# 读取数据
# ---------------------------------------------------------------------------
def load_json(name, default=None):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[build_seo] 读取 {name} 失败: {e}")
        return default

today = load_json("today.json", {}) or {}
promotions = load_json("promotions.json", []) or []
tools = load_json("tools.json", []) or []

prices = today.get("prices", []) or []
summary = today.get("summary", {}) or {}
changes = today.get("changes", []) or []
gen_at = today.get("generated_at", "") or today.get("date", "")
today_date = today.get("date", "")

def esc(s):
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))

def price_text(v, cur):
    if v is None:
        return "-"
    sym = "$" if cur == "USD" else ("¥" if cur == "CNY" else (cur or ""))
    try:
        fv = float(v)
    except Exception:
        return esc(v)
    if fv == 0:
        return sym + "0"
    return sym + ("%.3f" % fv if fv < 1 else "%.2f" % fv)

def ctx_text(n):
    try:
        n = int(n)
    except Exception:
        return "-"
    if n >= 1_000_000:
        return "%dM" % (n // 1_000_000)
    if n >= 1000:
        return "%dK" % (n // 1000)
    return str(n)

PAGE_CSS = """
:root{--bg:#0b1320;--panel:#0f1b2d;--border:#1e2a3a;--text:#e6edf6;--dim:#9fb3c8;--accent:#4ade80;--blue:#60a5fa}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'PingFang SC','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
.container{max-width:1100px;margin:0 auto;padding:24px 16px}
header{padding:28px 0 8px;border-bottom:1px solid var(--border)}
h1{font-size:24px;margin:0}
.sub{color:var(--dim);margin:6px 0 0;font-size:14px}
.back{display:inline-block;margin:16px 0;color:var(--blue);text-decoration:none;font-size:14px}
table{width:100%;border-collapse:collapse;margin:18px 0;font-size:14px}
th,td{border:1px solid var(--border);padding:9px 12px;text-align:left}
th{background:var(--panel);color:var(--dim);font-weight:600}
tr:nth-child(even) td{background:#0d1726}
a{color:var(--blue);text-decoration:none}
.badge{display:inline-block;padding:1px 8px;border-radius:6px;font-size:12px}
.b-long{background:rgba(74,222,128,.15);color:var(--accent)}
.b-lim{background:rgba(251,146,60,.18);color:#fb923c}
.card{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:14px 18px;margin:8px 0}
footer{margin-top:30px;padding:20px 0;color:var(--dim);font-size:13px;border-top:1px solid var(--border)}
"""

def page_head(title, sub):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(sub)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(sub)}">
<meta property="og:type" content="website">
<link rel="canonical" href="{SITE_URL}/">
</head>
<body>
<div class="container">
<header><h1>{esc(title)}</h1><p class="sub">{esc(sub)}</p></header>
<a class="back" href="{SITE_URL}/">← 返回交互主页（可搜索 / 筛选 / 看趋势）</a>
"""

def page_foot():
    upd = gen_at or today_date
    return f"""
<footer>
<p>数据更新时间：{esc(upd)}。本页为静态预渲染版本，供搜索引擎与爬虫抓取；完整交互体验请访问 <a href="{SITE_URL}/">主页</a>。</p>
<p>{esc(SITE_NAME_ZH)} · {esc(SITE_NAME_EN)}</p>
</footer>
</div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# prices.html
# ---------------------------------------------------------------------------
def build_prices():
    s = page_head(f"{SITE_NAME_ZH} · 实时价格表",
                  f"全球大模型 API 实时价格表（每百万 Token）：输入价、输出价、上下文窗口。更新于 {esc(gen_at)}。")
    s += "<div class='card'>"
    s += f"覆盖厂商 <b>{esc(summary.get('providers','-'))}</b> · 监控模型 <b>{esc(summary.get('total_models','-'))}</b> · "
    s += f"今日降价 <b>{esc(summary.get('price_down','-'))}</b> · 今日涨价 <b>{esc(summary.get('price_up','-'))}</b> · 新模型 <b>{esc(summary.get('new_models','-'))}</b>"
    s += "</div>"
    s += "<table><thead><tr><th>平台</th><th>代表模型</th><th>输入(每百万)</th><th>输出(每百万)</th><th>上下文窗口</th><th>来源</th><th>官网</th></tr></thead><tbody>"
    for p in prices:
        official = p.get("official_page") or ""
        link = f'<a href="{esc(official)}" target="_blank" rel="noopener">官网 ↗</a>' if official else "-"
        s += (f"<tr><td>{esc(p.get('provider',''))}</td><td>{esc(p.get('model',''))}</td>"
              f"<td>{price_text(p.get('input_price'), p.get('currency'))}</td>"
              f"<td>{price_text(p.get('output_price'), p.get('currency'))}</td>"
              f"<td>{ctx_text(p.get('context_window'))}</td>"
              f"<td>{esc(p.get('source',''))}</td><td>{link}</td></tr>")
    s += "</tbody></table>"
    # 今日变化
    if changes:
        s += "<h2>今日价格变化</h2><table><thead><tr><th>类型</th><th>平台 · 模型</th><th>说明</th></tr></thead><tbody>"
        for c in changes:
            s += f"<tr><td>{esc(c.get('type',''))}</td><td>{esc(c.get('provider',''))} · {esc(c.get('model',''))}</td><td>{esc(c.get('detail',''))}</td></tr>"
        s += "</tbody></table>"
    s += PAGE_CSS_BLOCK
    s += page_foot()
    write("prices.html", s)

# ---------------------------------------------------------------------------
# promotions.html
# ---------------------------------------------------------------------------
def build_promotions():
    s = page_head(f"{SITE_NAME_ZH} · 优惠活动",
                  "整理全球主流大模型厂商当前真实在行的优惠、限免与免费额度活动。")
    s += "<table><thead><tr><th>类型</th><th>厂商 · 活动</th><th>详情 / 来源</th></tr></thead><tbody>"
    for p in promotions:
        tag = p.get("tag", "")
        cls = "b-lim" if tag == "限免" else "b-long"
        url = p.get("url") or ""
        src = f' <a href="{esc(url)}" target="_blank" rel="noopener">来源 ↗</a>' if url else ""
        desc = p.get("description", "") or ""
        date = p.get("date", "") or ""
        detail = (esc(date) + ((" · " + esc(desc)) if desc else "")) + src
        s += (f"<tr><td><span class='badge {cls}'>{esc(tag)}</span></td>"
              f"<td>{esc(p.get('provider',''))} · {esc(p.get('title',''))}</td>"
              f"<td>{detail}</td></tr>")
    s += "</tbody></table>"
    s += PAGE_CSS_BLOCK
    s += page_foot()
    write("promotions.html", s)

# ---------------------------------------------------------------------------
# tools.html
# ---------------------------------------------------------------------------
def build_tools():
    s = page_head(f"{SITE_NAME_ZH} · 工具指南",
                  "精选 AI 对话、模型聚合、价格对比、API 调试与 AI 编程工具，附价格与套餐说明。")
    for cat in tools:
        s += f"<h2>{esc(cat.get('category', ''))}</h2>"
        s += "<div class='card'>"
        for it in cat.get("items", []):
            price = it.get("price", "") or ""
            s += (f"<p><b><a href='{esc(it.get('url',''))}' target='_blank' rel='noopener'>{esc(it.get('name',''))}</a></b>"
                  f" — {esc(it.get('desc',''))}<br><span style='color:var(--dim)'>价格 / 套餐：{esc(price)}</span></p>")
        s += "</div>"
    s += PAGE_CSS_BLOCK
    s += page_foot()
    write("tools.html", s)

PAGE_CSS_BLOCK = f"<style>{PAGE_CSS}</style>"

# ---------------------------------------------------------------------------
# sitemap.xml
# ---------------------------------------------------------------------------
def build_sitemap():
    urls = [
        ("/", "daily"),
        ("/prices.html", "daily"),
        ("/promotions.html", "daily"),
        ("/tools.html", "daily"),
    ]
    lastmod = (gen_at or today_date or datetime.date.today().isoformat())
    if "T" in lastmod:
        lastmod = lastmod.split("T")[0]
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for path, freq in urls:
        body.append("  <url>")
        body.append(f"    <loc>{SITE_URL}{path}</loc>")
        body.append(f"    <lastmod>{esc(lastmod)}</lastmod>")
        body.append(f"    <changefreq>{freq}</changefreq>")
        body.append(f"    <priority>{1.0 if path=='/' else 0.8}</priority>")
        body.append(f'    <xhtml:link rel="alternate" hreflang="zh-CN" href="{SITE_URL}{path}"/>')
        body.append(f'    <xhtml:link rel="alternate" hreflang="en" href="{SITE_URL}{path}"/>')
        body.append("  </url>")
    body.append("</urlset>")
    write("sitemap.xml", "\n".join(body))

# ---------------------------------------------------------------------------
# robots.txt
# ---------------------------------------------------------------------------
def build_robots():
    txt = f"""User-agent: *
Allow: /

# 静态预渲染页（SEO 友好，优先抓取）
Allow: /prices.html
Allow: /promotions.html
Allow: /tools.html
Allow: /api/

Sitemap: {SITE_URL}/sitemap.xml
"""
    write("robots.txt", txt)

# ---------------------------------------------------------------------------
# llms.txt
# ---------------------------------------------------------------------------
def build_llms():
    lines = [
        f"# {SITE_NAME_ZH} / {SITE_NAME_EN}",
        "",
        f"> 自动追踪全球大模型 API 价格、优惠活动与工具指南的每日更新站点。数据由爬虫每日采集，覆盖主流及国内厂商。更新于 {gen_at or today_date}。",
        "",
        "## Data (machine-readable, CORS-enabled)",
        f"- 实时价格表 (JSON): {SITE_URL}/api/prices.json",
        f"- 优惠活动 (JSON): {SITE_URL}/api/promotions.json",
        f"- 工具指南 (JSON): {SITE_URL}/api/tools.json",
        f"- 历史价格趋势 (JSON): {SITE_URL}/data/history.json",
        "",
        "## Pages",
        f"- 交互主页（搜索/筛选/趋势）: {SITE_URL}/",
        f"- 静态价格表（SEO）: {SITE_URL}/prices.html",
        f"- 优惠活动: {SITE_URL}/promotions.html",
        f"- 工具指南: {SITE_URL}/tools.html",
        "",
        "## Notes",
        "- 价格单位：每百万 Token（1M tokens）。",
        "- `source=openrouter_api|official` 为实时采集价；`source=fallback` 为官网不可达时的国内直连参考价。",
    ]
    write("llms.txt", "\n".join(lines))

# ---------------------------------------------------------------------------
# _headers (CORS for data & api on Cloudflare Pages / Netlify)
# ---------------------------------------------------------------------------
def build_headers():
    txt = """/data/*.json
  Access-Control-Allow-Origin: *
  Cache-Control: public, max-age=300

/api/*.json
  Access-Control-Allow-Origin: *
  Cache-Control: public, max-age=300
"""
    write("_headers", txt)

# ---------------------------------------------------------------------------
# api endpoints (clean public surface)
# ---------------------------------------------------------------------------
def build_api():
    api_dir = os.path.join(OUT, "api")
    os.makedirs(api_dir, exist_ok=True)
    wrap = {
        "generated_at": gen_at,
        "date": today_date,
        "summary": summary,
        "changes": changes,
        "prices": prices,
    }
    write_json("api/prices.json", wrap)
    write_json("api/promotions.json", promotions)
    write_json("api/tools.json", tools)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def write(name, content):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[build_seo] 生成 {name}")

def write_json(name, obj):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"[build_seo] 生成 {name}")

if __name__ == "__main__":
    build_prices()
    build_promotions()
    build_tools()
    build_api()
    build_sitemap()
    build_robots()
    build_llms()
    build_headers()
    print("[build_seo] 全部完成。")
