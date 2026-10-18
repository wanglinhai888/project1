"""AI 润色 + SEO/GEO 增强：把每日价格变化摘要改写成发布级文章。

设计（遵循项目"失败不阻断主流程"原则）：
- 可插拔 LLM provider：gemini | openrouter | openai | groq | deepseek
- 凭据 / 模型均走环境变量，不硬编码：
    LLM_PROVIDER  (默认 openrouter)
    LLM_API_KEY
    LLM_MODEL     (各 provider 默认一个免费模型)
- 无 Key 或调用失败时 enhance() 返回 None，调用方降级为原始 summary，绝不阻断当天发布。
- 依赖：项目已有的 requests（爬虫 requirements 中已安装）；无 requests 时同样降级。
"""
import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawler.config import DATA_DIR
from publisher.summary import build_summary, load_today

try:
    import requests
except Exception:  # pragma: no cover - 依赖缺失时降级
    requests = None


# 各 provider 的默认（尽量免费）模型
DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openrouter": "meta-llama/llama-3.1-8b-instruct:free",
    "openai": "gpt-4o-mini",
    "groq": "llama-3.1-8b-instant",
    "deepseek": "deepseek-chat",
}

# OpenAI 兼容接口的 base url
_COMPAT_BASE = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "deepseek": "https://api.deepseek.com/v1",
}

PROMPT = """你是一名资深科技内容编辑，负责把一份"AI 大模型每日价格变化"数据改写为面向公众号 / 自媒体的发布文章。

【原始变化数据】
{raw}

【网站与引用】
站点: {site}
实时价格表: {site}/prices.html
数据中的"官网:"字段为对应模型官方定价页，请在文中以超链接 [文字](链接) 形式引用。

【任务要求】
1. 忠实于原始数据：所有价格数字、涨跌方向、模型 / 厂商名称必须与原始数据完全一致，严禁编造或改动任何数字。
2. 改写成通顺、有重点、可读性强的中文文章：一句导语（直接给出今日核心结论），再按"涨价 / 降价 / 新模型"分组叙述，结尾给一段简要行业观察。
3. SEO 优化：给出 title（含核心关键词"AI 大模型 价格 日报/变动"，≤30 字）、meta_description（≤120 字，含关键词）、keywords（逗号分隔，8 个以内，含主要厂商与"价格/降价/涨价"）。
4. GEO 优化（面向 ChatGPT / Perplexity / 豆包 / 文心等生成式引擎）：
   - 使用完整实体名（如"OpenAI GPT-5"而非"GPT-5"），关键结论用独立陈述句，便于被直接引用。
   - 生成 3-5 条 FAQ（常见问题），每条约 1-2 句直接回答，覆盖"今日哪些模型降价 / 涨价""新上线了哪些模型""数据来源与更新频率"。
5. 输出严格 JSON，字段如下（article 使用 Markdown：可含 ## 小标题、**加粗**、- 列表、[文字](链接)）：
{{
  "title": "...",
  "meta_description": "...",
  "keywords": "词1,词2,...",
  "article": "Markdown 文章正文",
  "faq": [{{"q": "...", "a": "..."}}, ...]
}}
只输出 JSON，不要任何额外说明文字。"""


def _compat_payload(model, prompt):
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.4,
    }


def _gemini_payload(model, prompt):
    return {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }


def _call(provider, api_key, model, prompt, timeout=60):
    if provider == "gemini":
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        resp = requests.post(url, json=_gemini_payload(model, prompt), timeout=timeout)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    url = f"{_COMPAT_BASE[provider]}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(
        url, headers=headers, json=_compat_payload(model, prompt), timeout=timeout
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _build_raw_context(today):
    """把变化数据整理成带官方链接的结构化上下文，供 LLM 引用。"""
    changes = today.get("changes", []) or []
    price_by_key = {
        (p["provider"], p["model"]): p for p in today.get("prices", [])
    }
    lines = []
    for c in changes:
        p = price_by_key.get((c["provider"], c["model"]), {})
        official = p.get("official_page", "") or ""
        lines.append(
            f"- {c['provider']} {c['model']} | 类型={c.get('type')} | "
            f"{c.get('detail', '')} | 官网: {official}"
        )
    return "\n".join(lines) if lines else "(今日无价格变动)"


def enhance(today=None, site=None, provider=None, api_key=None, model=None):
    """调用 LLM 生成增强文章。任何异常 / 无 Key 都返回 None（交由上层降级）。"""
    provider = (provider or os.environ.get("LLM_PROVIDER", "openrouter")).lower()
    api_key = api_key or os.environ.get("LLM_API_KEY")
    model = model or os.environ.get("LLM_MODEL") or DEFAULT_MODELS.get(provider)
    site = (site or os.environ.get("SITE_URL", "https://www.codenav.cn")).rstrip("/")

    if not api_key or requests is None or provider not in DEFAULT_MODELS:
        return None

    if today is None:
        today = load_today()
    summary = build_summary(today)
    raw = _build_raw_context(today)
    prompt = PROMPT.format(raw=raw, site=site)

    try:
        text = _call(provider, api_key, model, prompt)
        data = json.loads(text)
    except Exception as exc:  # 网络 / 解析 / 限流 等均降级
        print(f"[enhance] LLM 调用失败，降级为原始摘要: {exc}")
        return None

    data.setdefault("date", today.get("date", ""))
    data.setdefault("article", summary["text"])
    data.setdefault("faq", [])
    data.setdefault("title", summary["title"])
    data.setdefault("meta_description", "")
    data.setdefault("keywords", "")
    data["provider"] = provider
    data["model"] = model
    return data


def save_markdown(data, out_dir):
    """生成给发布渠道用的 Markdown 全文（含标题/元信息）。"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    md = f"# {data.get('title', '')}\n\n"
    if data.get("meta_description"):
        md += f"> {data['meta_description']}\n\n"
    md += data.get("article", "")
    path = out_dir / f"article_{data.get('date', '')}.md"
    path.write_text(md, encoding="utf-8")
    return path


def main():
    ap = argparse.ArgumentParser(description="AI 润色 + SEO/GEO 增强（无 Key 自动降级）")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--site", default=None)
    ap.add_argument("--out", default=str(PROJECT_ROOT / "publisher" / "output"))
    args = ap.parse_args()

    today = load_today()
    data = enhance(
        today, site=args.site, provider=args.provider,
        api_key=args.api_key, model=args.model,
    )
    if data is None:
        print("[enhance] 未生成增强文章（无 API Key / 调用失败），保留原始摘要，不阻断流程。")
        return

    # 结构化 JSON 落库（随仓库提交，供网站文章页与各渠道 sink 复用）
    json_path = DATA_DIR / f"article_{data['date']}.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[enhance] 已生成 {json_path}")

    md_path = save_markdown(data, args.out)
    print(f"[enhance] 已生成 {md_path}")


if __name__ == "__main__":
    main()
