"""OpenAI 价格采集。

价格页 https://openai.com/api/pricing/ 为客户端渲染（Next.js App Router），
价格数据以内嵌 JSON 形式输出到 HTML（self.__next_f.push），结构形如：
    "name":"GPT-5.6 Sol", ... "Input:\\n$5.00 / 1M tokens ... Output:\\n$30.00 / 1M tokens"

解析策略：
1. 提取 Next.js 内嵌文本（解码 RSC 转义）；
2. 用「完整模型名 + Input/Output 价格」正则精确匹配（避免匹配到导航栏模型名）；
3. 匹配失败或抓取失败时使用内置参考价兜底。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
import json
import re

from spiders.base import Spider


class OpenAISpider(Spider):
    provider = "OpenAI"
    pricing_url = "https://openai.com/api/pricing/"

    # 单位：USD / 百万 Token
    MODEL_CATALOG = {
        "GPT-5.6 Sol": {"category": "LLM", "context_window": 1500000, "input_price": 5.00, "output_price": 30.00},
        "GPT-5.6 Terra": {"category": "LLM", "context_window": 1500000, "input_price": 2.50, "output_price": 15.00},
        "GPT-5.6 Luna": {"category": "LLM", "context_window": 1500000, "input_price": 1.00, "output_price": 1.20},
        "GPT-4o": {"category": "LLM", "context_window": 128000, "input_price": 2.50, "output_price": 10.00},
        "GPT-4o mini": {"category": "LLM", "context_window": 128000, "input_price": 0.15, "output_price": 0.60},
        "o3": {"category": "Reasoner", "context_window": 200000, "input_price": 2.00, "output_price": 8.00},
        "o3 mini": {"category": "Reasoner", "context_window": 200000, "input_price": 1.10, "output_price": 4.40},
        "o4 mini": {"category": "Reasoner", "context_window": 200000, "input_price": 1.10, "output_price": 4.40},
    }

    def parse(self, html: str) -> list:
        text = self._nextjs_text(html) or self.plain_text(html)
        prices = []
        for model, meta in self.MODEL_CATALOG.items():
            inp, out = self._find_price(text, model)
            if inp is not None and out is not None:
                prices.append(self._official_entry(model, meta, inp, out))
        return prices

    def _find_price(self, text: str, model: str):
        """匹配内嵌 JSON 中「完整模型名 + Input/Output 价格」片段。

        注意：RSC 转义文本解码后，价格描述中的换行是字面 "\\n"（反斜杠+n），
        因此使用 .*? 宽容匹配，而非 \\s*。
        """
        pattern = re.compile(
            r'"name":"' + re.escape(model)
            + r'".*?Input:.*?\$([\d.]+) / 1M tokens.*?Output:.*?\$([\d.]+) / 1M tokens',
            re.S,
        )
        m = pattern.search(text)
        if m:
            return float(m.group(1)), float(m.group(2))
        return None, None

    def _nextjs_text(self, html: str) -> str:
        """提取 Next.js 内嵌数据文本（App Router 的 __next_f 与 Pages 的 __NEXT_DATA__）。"""
        parts = []
        pattern = re.compile(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)')
        for m in pattern.finditer(html):
            raw = m.group(1)
            try:
                parts.append(json.loads('"' + raw + '"'))
            except Exception:
                parts.append(raw)
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if m:
            try:
                parts.append(json.dumps(json.loads(m.group(1)), ensure_ascii=False))
            except Exception:
                pass
        return " ".join(parts)
