"""AI 大模型价格雷达 - 主流程。

每天由 GitHub Actions 调用：python crawler/main.py
流程：加载爬虫 -> 采集价格 -> 读取历史 -> 计算变化 -> 生成 JSON -> 同步网站数据。

运行位置：项目根目录（crawler 目录的上一级）。
"""
import argparse
import importlib
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawler.config import DATA_FILES, SPIDER_MODULES, TIMEZONE
from processors.json_export import (
    export_history,
    export_models,
    export_promotions,
    export_today,
    sync_to_website,
)
from processors.price_compare import compare_prices


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def read_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logging.getLogger("main").warning("读取 %s 失败，使用默认值: %s", path, exc)
        return default


def load_spiders():
    """按配置注册表动态加载爬虫实例。"""
    spiders = []
    for module_path in SPIDER_MODULES:
        mod_name, cls_name = module_path.rsplit(".", 1)
        try:
            mod = importlib.import_module(mod_name)
            spiders.append(getattr(mod, cls_name)())
        except Exception as exc:
            logging.getLogger("main").error("加载爬虫 %s 失败: %s", module_path, exc)
    return spiders


def _norm_model(name):
    return (name or "").strip().lower()


# 厂商名归一化（官网爬虫中文命名 -> OpenRouter 英文命名），用于判断同厂商是否已被 API 覆盖
_PROVIDER_NORM = {
    "阿里云": "alibaba", "alibaba": "alibaba",
    "腾讯云": "tencent", "tencent": "tencent",
    "bigmodel (智谱ai)": "z.ai", "z.ai": "z.ai", "智谱ai": "z.ai",
    "小米 mimo": "xiaomi", "xiaomi": "xiaomi",
    "aws": "amazon", "amazon": "amazon",
    "火山引擎": "volcengine", "火山": "volcengine",
    "硅基流动": "siliconflow", "模力方舟": "modelark",
    "byteplus": "byteplus",
}


def _norm_provider(name):
    return _PROVIDER_NORM.get((name or "").strip().lower(), (name or "").strip().lower())


def merge_prices(raw):
    """按优先级合并多爬虫结果，杜绝写死价与真实价并存。

    优先级：
      1. OpenRouter API 真实价(openrouter_api) 作基座（覆盖绝大多数厂商）
      2. 官网 official（静态站真抓到的，如 DeepSeek）直接保留
      3. 官网 fallback（写死参考价）仅当「该厂商未被 OpenRouter 覆盖」且
         「该模型未被 API 覆盖」时保留——即只保留火山/硅基/模力方舟/BytePlus
         等 OpenRouter 没有的国内直连专属；其余国际/国内主流厂商的写死价一律丢弃，
         因为它们的真实价已由 OpenRouter 提供。
    """
    openrouter, rest = [], []
    for p in raw:
        if p.get("source") == "openrouter_api":
            openrouter.append(p)
        else:
            rest.append(p)

    covered_models = {_norm_model(p["model"]) for p in openrouter}
    or_providers = {_norm_provider(p["provider"]) for p in openrouter}
    result = {}
    for p in openrouter:
        result[(p["provider"], p["model"])] = p
    dropped = 0
    for p in rest:
        if p.get("source") == "official":
            # 官网真抓到的价格，保留（与 OpenRouter 真价并存无害）
            result.setdefault((p["provider"], p["model"]), p)
            continue
        # 写死参考价：同厂商或同模型已被 OpenRouter 真实价覆盖则丢弃
        np = _norm_provider(p["provider"])
        if np in or_providers or _norm_model(p["model"]) in covered_models:
            logging.info("丢弃写死价(OpenRouter 已覆盖: %s/%s)", p["provider"], p["model"])
            dropped += 1
            continue
        result.setdefault((p["provider"], p["model"]), p)
    if dropped:
        logging.info("已丢弃 %d 个被 OpenRouter 真实价覆盖的写死价条目", dropped)
    return list(result.values())


def build_snapshot(prices, date_str):
    """把今日价格转为历史快照记录（不覆盖旧数据，按天追加）。"""
    return [
        {
            "date": date_str,
            "provider": p["provider"],
            "model": p["model"],
            "input_price": p["input_price"],
            "output_price": p["output_price"],
            "currency": p["currency"],
            "source": p.get("source", "fallback"),
        }
        for p in prices
    ]


def upsert_snapshot(history, snapshot, date_str):
    """当天已存在快照时替换（防止重复运行叠加），并按日期排序。"""
    history = [e for e in history if e.get("date") != date_str]
    history.extend(snapshot)
    history.sort(key=lambda e: e["date"])
    return history


def build_models(prices):
    """从价格列表提取模型基础信息。"""
    seen, models = set(), []
    for p in prices:
        key = (p["provider"], p["model"])
        if key in seen:
            continue
        seen.add(key)
        models.append({
            "provider": p["provider"],
            "model": p["model"],
            "category": p.get("category", "LLM"),
            "context_window": p.get("context_window"),
        })
    return models


def build_today(prices, changes, date_str, generated_at):
    """组装 today.json。"""
    up = [c for c in changes if c["type"] == "price_up"]
    down = [c for c in changes if c["type"] == "price_down"]
    new_models = [c for c in changes if c["type"] == "new_model"]
    return {
        "date": date_str,
        "generated_at": generated_at,
        "prices": prices,
        "changes": changes,
        "new_models": [
            {"provider": c["provider"], "model": c["model"], "type": c["type"]}
            for c in new_models
        ],
        "summary": {
            "total_models": len(prices),
            "providers": len({p["provider"] for p in prices}),
            "price_up": len(up),
            "price_down": len(down),
            "new_models": len(new_models),
        },
    }


def get_local_tz():
    """获取北京时间时区；缺少 IANA 时区库（如部分 Windows 环境）时退化为固定 UTC+8。"""
    try:
        return ZoneInfo(TIMEZONE)
    except Exception:
        logging.getLogger("main").warning("无法加载 %s 时区，使用固定 UTC+8", TIMEZONE)
        return timezone(timedelta(hours=8))


def main():
    parser = argparse.ArgumentParser(description="AI 大模型价格雷达 - 数据采集")
    parser.add_argument(
        "--offline", action="store_true",
        help="跳过网络抓取，仅使用内置参考价生成数据（用于本地/CI 快速验证流程）",
    )
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("main")
    now = datetime.now(get_local_tz())
    date_str = now.strftime("%Y-%m-%d")
    logger.info("========== AI 大模型价格雷达 开始运行 %s ==========", date_str)

    # 1. 采集
    spiders = load_spiders()
    for spider in spiders:
        spider.offline = args.offline
    if args.offline:
        logger.info("离线模式：跳过网络抓取，使用内置参考价")
    raw_prices = []
    empty_providers = []
    for spider in spiders:
        try:
            prices = spider.crawl()
        except Exception as exc:
            logger.error("[%s] 采集异常: %s", spider.provider, exc)
            prices = []
        if prices:
            raw_prices.extend(prices)
        else:
            empty_providers.append(spider.provider)

    # 按优先级合并：OpenRouter API 真实价 > 官网 official > 官网 fallback(仅未覆盖时保留)
    all_prices = merge_prices(raw_prices)
    logger.info(
        "合并完成: %d 个模型 (OpenRouter API 真实价源优先，丢弃被覆盖的写死价)",
        len(all_prices),
    )

    # 2. 历史
    history = read_json(DATA_FILES["history"], [])
    snapshot = build_snapshot(all_prices, date_str)
    history = upsert_snapshot(history, snapshot, date_str)

    # 3. 分析
    changes = compare_prices(all_prices, history, exclude_date=date_str)
    today = build_today(
        all_prices, changes, date_str, now.isoformat(timespec="seconds")
    )
    models = build_models(all_prices)
    promotions = read_json(DATA_FILES["promotions"], [])

    # 4. 导出
    export_history(history)
    export_today(today)
    export_models(models)
    export_promotions(promotions)
    sync_dir, copied = sync_to_website()

    # 5. 报告
    s = today["summary"]
    logger.info(
        "运行完成: %d 个模型 / %d 家厂商 / 涨价 %d / 降价 %d / 新模型 %d",
        s["total_models"], s["providers"], s["price_up"], s["price_down"], s["new_models"],
    )
    logger.info("已同步到网站目录: %s (%s)", sync_dir, ", ".join(copied))
    if empty_providers:
        logger.warning("以下厂商未获取到官网数据(已用内置参考价): %s", ", ".join(empty_providers))


if __name__ == "__main__":
    main()
