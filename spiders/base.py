"""爬虫抽象基类与通用解析工具。

统一爬虫接口：
    class Spider:
        def crawl(self) -> list[dict]   # 统一入口

输出标准价格条目：
    {
        "provider": "OpenAI",
        "model": "GPT-5",
        "category": "LLM",
        "context_window": 400000,
        "input_price": 1.25,          # 每百万 Token 输入价格
        "output_price": 10.0,         # 每百万 Token 输出价格
        "currency": "USD",
        "unit": "per_1M_tokens",
        "source": "official|fallback",
        "official_page": "...",
    }

兜底策略：网页解析失败时使用各厂商内置参考价（source=fallback），
保证网站始终有数据可展示；是否抓取成功通过 source 字段区分。
"""
import logging
import re
import time
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup

from crawler.config import REQUEST_TIMEOUT, RETRY_BACKOFF, RETRY_TIMES, USER_AGENT

logger = logging.getLogger(__name__)

UNIT = "per_1M_tokens"


class Spider(ABC):
    """所有厂商爬虫的基类。"""

    provider = ""            # 厂商名
    pricing_url = ""         # 官方价格页
    MODEL_CATALOG = {}       # model -> {category, context_window, input_price, output_price, currency}

    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.offline = False  # True 时跳过网络请求，仅输出内置参考价（用于本地/CI 快速验证）

    # ---------- 对外统一接口 ----------
    def crawl(self) -> list:
        """抓取网页 -> 解析 -> 合并内置兜底，返回标准价格列表（永不抛异常）。"""
        official = []
        try:
            html = "" if self.offline else self.fetch()
            official = self.parse(html) or []
        except Exception as exc:
            logger.warning("[%s] 抓取/解析失败，使用内置参考价: %s", self.provider, exc)
        prices = self._merge_fallback(official)
        logger.info(
            "[%s] 采集结果: 官网解析 %d 个, 内置参考 %d 个",
            self.provider, len(official), len(prices) - len(official),
        )
        return prices

    @abstractmethod
    def parse(self, html: str) -> list:
        """子类实现：把网页 HTML 解析为标准价格列表（仅返回官网解析结果）。"""
        raise NotImplementedError

    # ---------- 请求 ----------
    def fetch(self, url: str | None = None) -> str:
        target = url or self.pricing_url
        last_error = None
        for attempt in range(RETRY_TIMES):
            try:
                resp = self.session.get(target, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding or resp.encoding or "utf-8"
                return resp.text
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "[%s] 请求失败(第 %d/%d 次): %s", self.provider, attempt + 1, RETRY_TIMES, exc
                )
                if attempt < RETRY_TIMES - 1:
                    time.sleep(RETRY_BACKOFF * (attempt + 1))
        raise last_error

    # ---------- 通用解析工具 ----------
    @staticmethod
    def soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    @staticmethod
    def plain_text(html: str) -> str:
        """去掉 script/style 后的纯文本。"""
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text("\n", strip=True)

    @staticmethod
    def parse_tables(soup: BeautifulSoup) -> list:
        """返回页面所有表格的行文本列表。"""
        rows = []
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
                if cells:
                    rows.append(cells)
        return rows

    @staticmethod
    def _to_float(s: str) -> float:
        return float(s.replace(",", "").replace("$", "").strip())

    # ---------- 兜底合并 ----------
    def _merge_fallback(self, official: list) -> list:
        seen = set()
        prices = []
        for p in official:
            p.setdefault("source", "official")
            p.setdefault("official_page", self.pricing_url)
            seen.add((p["provider"], p["model"]))
            prices.append(p)
        for model, meta in self.MODEL_CATALOG.items():
            if (self.provider, model) in seen:
                continue
            prices.append(self._fallback_entry(model, meta))
        return prices

    def _fallback_entry(self, model: str, meta: dict) -> dict:
        return {
            "provider": self.provider,
            "model": model,
            "category": meta.get("category", "LLM"),
            "context_window": meta.get("context_window"),
            "input_price": meta["input_price"],
            "output_price": meta["output_price"],
            "currency": meta.get("currency", "USD"),
            "unit": UNIT,
            "source": "fallback",
            "official_page": self.pricing_url,
        }

    def _official_entry(self, model: str, meta: dict, input_price: float,
                        output_price: float, currency: str | None = None) -> dict:
        return {
            "provider": self.provider,
            "model": model,
            "category": meta.get("category", "LLM"),
            "context_window": meta.get("context_window"),
            "input_price": round(float(input_price), 4),
            "output_price": round(float(output_price), 4),
            "currency": currency or meta.get("currency", "USD"),
            "unit": UNIT,
            "source": "official",
            "official_page": self.pricing_url,
        }


# ---------- 通用价格匹配工具 ----------

def find_io_prices(text: str, model: str, max_span: int = 4000):
    """在文本中定位模型名，提取其后的输入/输出价格。

    支持 "$X" 与 "X元" 两种写法；返回 (input_price, output_price)，
    未找到时返回 (None, None)。
    """
    for m in re.finditer(re.escape(model), text, re.I):
        seg = text[m.end(): m.end() + max_span]
        inp = _price_after(seg, ("input", "输入"))
        out = _price_after(seg, ("output", "输出"))
        if inp is not None and out is not None:
            return inp, out
    return None, None


def _price_after(seg: str, keywords: tuple) -> float | None:
    seg_lower = seg.lower()
    for kw in keywords:
        idx = seg_lower.find(kw.lower())
        if idx == -1:
            continue
        # 防御：input 前 80 字符内出现 cached/缓存/命中 时跳过，避免取到缓存价
        before = seg[max(0, idx - 80):idx].lower()
        if kw in ("input", "输入") and any(
            w in before for w in ("cached", "cache", "缓存", "hit")
        ):
            continue
        window = seg[idx: idx + 200]
        m = re.search(r"\$\s?([\d][\d.,]*)", window)
        if m:
            return float(m.group(1).replace(",", ""))
        m = re.search(r"([\d][\d.,]*)\s*元", window)
        if m:
            return float(m.group(1).replace(",", ""))
    return None
