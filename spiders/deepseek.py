"""DeepSeek 价格采集。

价格页 https://api-docs.deepseek.com/quick_start/pricing 为文档站，
价格表结构为行式（竖排模型列）：
    MODEL | deepseek-v4-flash | deepseek-v4-pro | ...
    1M INPUT TOKENS (CACHE MISS) | OFF-PEAK | $0.22 | $0.66 | ...
    1M OUTPUT TOKENS | OFF-PEAK | $0.66 | $1.98 | ...

解析策略：定位 CACHE MISS 输入行与输出行，按列读取各模型价格（取 OFF-PEAK 档）。

内置参考价基于官方公开定价整理，仅作兜底展示，请以官网为准。
"""
import re

from spiders.base import Spider


class DeepSeekSpider(Spider):
    provider = "DeepSeek"
    pricing_url = "https://api-docs.deepseek.com/quick_start/pricing"

    # 官网表格列名 -> 价格表统一模型名
    _ALIASES = {
        "deepseek-v4-flash": "V4-Flash",
        "deepseek-v4-pro": "V4-Pro",
        "deepseek-v4-flash-vision-exp": "V4-Flash-Vision-Exp",
    }

    # 单位：USD / 百万 Token（OFF-PEAK 档）
    MODEL_CATALOG = {
        "V4-Flash": {"category": "LLM", "context_window": 1000000, "input_price": 0.22, "output_price": 0.66},
        "V4-Pro": {"category": "LLM", "context_window": 1000000, "input_price": 0.66, "output_price": 1.98},
        "V4-Flash-Vision-Exp": {"category": "Multimodal", "context_window": 1000000, "input_price": 0.22, "output_price": 0.66},
    }

    def parse(self, html: str) -> list:
        rows = self.parse_tables(self.soup(html))
        if not rows or "MODEL" not in rows[0][0].upper():
            return []
        # 表头行：MODEL | 模型1 | 模型2 | ...
        model_names = [c for c in rows[0][1:] if c and c != "✓"]
        if not model_names:
            return []

        input_row = output_row = None
        for row in rows:
            label = row[0].upper()
            if "CACHE MISS" in label and "INPUT" in label:
                input_row = row
            elif "OUTPUT" in label and "TOKENS" in label:
                output_row = row
        if not input_row or not output_row:
            return []

        prices = []
        for idx, name in enumerate(model_names):
            catalog_name = self._ALIASES.get(name, name)
            meta = self.MODEL_CATALOG.get(catalog_name)
            if not meta:
                continue
            col = idx + 2  # 价格行结构: [标签, 时段, 模型1, 模型2, ...]
            if col >= len(input_row) or col >= len(output_row):
                continue
            try:
                inp = self._to_float(input_row[col])
                out = self._to_float(output_row[col])
            except ValueError:
                continue
            prices.append(self._official_entry(catalog_name, meta, inp, out))
        return prices
