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
import re
import glob
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = HERE
# 项目根 data 目录（crawler 产出 + publisher 增强文章落库处）
ROOT_DATA = os.path.join(os.path.dirname(HERE), "data")

SITE_URL = os.environ.get("SITE_URL", "https://www.codenav.cn").rstrip("/")
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

def page_head(title, sub, canon):
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
<link rel="canonical" href="{SITE_URL}{canon}">
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
                  f"全球大模型 API 实时价格表（每百万 Token）：输入价、输出价、上下文窗口。更新于 {esc(gen_at)}。",
                  "/prices")
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
                  "整理全球主流大模型厂商当前真实在行的优惠、限免与免费额度活动。",
                  "/promotions")
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
                  "精选 AI 对话、模型聚合、价格对比、API 调试与 AI 编程工具，附价格与套餐说明。",
                  "/tools")
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

ARTICLE_CSS = """
.article{max-width:840px;line-height:1.9;font-size:16px;margin:0 auto}
.article h1{font-size:26px;margin:20px 0 12px}
.article h2{font-size:21px;margin:28px 0 10px;padding-left:11px;border-left:4px solid var(--accent)}
.article h3{font-size:18px;margin:20px 0 8px;color:var(--accent-blue)}
.article p{margin:12px 0}
.article ul{margin:12px 0;padding-left:22px}
.article li{margin:8px 0}
.article a{color:var(--accent-blue);text-decoration:none}
.faq .card p{margin:6px 0}
"""
ARTICLE_CSS_BLOCK = f"<style>{ARTICLE_CSS}</style>"

# ---------------------------------------------------------------------------
# sitemap.xml
# ---------------------------------------------------------------------------
def build_sitemap():
    urls = [
        ("/", "daily"),
        ("/prices", "daily"),
        ("/promotions", "daily"),
        ("/tools", "daily"),
        ("/article", "daily"),
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
Allow: /prices
Allow: /promotions
Allow: /tools
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
        f"- 每日价格日报（SEO/GEO 文章页）: {SITE_URL}/article.html",
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
# article.html（每日 SEO/GEO 文章页，含 JSON-LD 结构化数据）
# ---------------------------------------------------------------------------
def inline_md(s):
    """Markdown 行内元素转 HTML：转义 -> 链接 -> 加粗。"""
    s = esc(s)
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
               r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    return s


def md_to_html(md):
    """极简 Markdown -> HTML（仅覆盖本场景受控输出：标题/列表/段落/链接/加粗）。"""
    if not md:
        return ""
    out, in_list = [], False
    for line in md.split("\n"):
        s = line.strip()
        if s.startswith("### "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<h3>{esc(s[4:])}</h3>")
        elif s.startswith("## "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<h2>{esc(s[3:])}</h2>")
        elif s.startswith("# "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<h1>{esc(s[2:])}</h1>")
        elif s.startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{inline_md(s[2:])}</li>")
        elif s == "":
            if in_list:
                out.append("</ul>"); in_list = False
        else:
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<p>{inline_md(s)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def fallback_article_html():
    """无 AI 增强文章时，用原始变化数据兜底渲染。"""
    if not changes:
        return "<p>今日价格无变动。</p>"
    rows = "".join(
        f"<li>{esc(c.get('provider', ''))} {esc(c.get('model', ''))}：{esc(c.get('detail', ''))}</li>"
        for c in changes
    )
    return (
        f"<p>今日共追踪 {esc(summary.get('total_models', '-'))} 个模型，"
        f"覆盖 {esc(summary.get('providers', '-'))} 家厂商；"
        f"涨价 {esc(summary.get('price_up', '-'))}、降价 {esc(summary.get('price_down', '-'))}、"
        f"新模型 {esc(summary.get('new_models', '-'))}。</p>"
        f"<p>详细变动：</p><ul>{rows}</ul>"
        f"<p>完整实时价格见 <a href='{SITE_URL}/prices.html'>价格表</a>。</p>"
    )


def build_article():
    date = today_date
    art = None
    art_path = os.path.join(ROOT_DATA, f"article_{date}.json")
    if not os.path.exists(art_path):
        # 当日 AI 文章缺失时，回退到最近一期，避免退化成无样式的干列表
        cands = sorted(glob.glob(os.path.join(ROOT_DATA, "article_*.json")), reverse=True)
        if cands:
            art_path = cands[0]
            print(f"[build_seo] 未找到当日文章 article_{date}.json，改用 {os.path.basename(art_path)}")
    if os.path.exists(art_path):
        try:
            with open(art_path, "r", encoding="utf-8") as f:
                art = json.load(f)
        except Exception as e:
            print(f"[build_seo] 读取 {art_path} 失败: {e}")

    if art:
        title = art.get("title") or f"{SITE_NAME_ZH} · 每日价格日报（{date}）"
        desc = art.get("meta_description") or f"每日追踪全球大模型 API 价格变动，更新于 {date}。"
        keywords = art.get("keywords") or "AI大模型,价格,降价,涨价"
        body_md = art.get("article", "")
        # 文章正文开头的 "# 标题" 与页面 <h1> 重复，去掉首行 H1
        if body_md.lstrip().startswith("# "):
            body_md = body_md.lstrip()
            body_md = body_md[body_md.find("\n") + 1:].lstrip()
        body_html = md_to_html(body_md)
        faq = art.get("faq") or []
    else:
        title = f"{SITE_NAME_ZH} · 每日价格日报（{date}）"
        desc = f"每日追踪全球大模型 API 价格变动，更新于 {date}。"
        keywords = "AI大模型,价格,降价,涨价"
        body_html = fallback_article_html()
        faq = []

    modified = (gen_at.split("T")[0] if "T" in gen_at else gen_at) or date
    article_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": desc,
        "datePublished": date,
        "dateModified": modified,
        "author": {"@type": "Organization", "name": SITE_NAME_ZH},
        "publisher": {"@type": "Organization", "name": SITE_NAME_ZH},
        "mainEntityOfPage": {"@type": "WebPage", "@id": f"{SITE_URL}/article.html"},
    }
    ld = f'<script type="application/ld+json">{json.dumps(article_ld, ensure_ascii=False)}</script>'
    if faq:
        faq_ld = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q.get("q", ""),
                 "acceptedAnswer": {"@type": "Answer", "text": q.get("a", "")}}
                for q in faq
            ],
        }
        ld += f'\n<script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False)}</script>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="keywords" content="{esc(keywords)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<link rel="canonical" href="{SITE_URL}/article.html">
{ld}
</head>
<body>
<div class="container">
<header><h1>{esc(title)}</h1><p class="sub">{esc(desc)}</p></header>
<a class="back" href="{SITE_URL}/">← 返回交互主页（可搜索 / 筛选 / 看趋势）</a>
<div class="article">{body_html}</div>
"""
    if faq:
        html += "<h2>常见问题（FAQ）</h2><div class='faq'>"
        for q in faq:
            html += (f"<div class='card'><p><b>Q：{esc(q.get('q', ''))}</b></p>"
                     f"<p>{esc(q.get('a', ''))}</p></div>")
        html += "</div>"
    html += PAGE_CSS_BLOCK + ARTICLE_CSS_BLOCK
    html += page_foot()
    write("article.html", html)


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
    build_article()
    build_api()
    build_sitemap()
    build_robots()
    build_llms()
    build_headers()
    print("[build_seo] 全部完成。")
