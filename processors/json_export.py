"""JSON 数据导出：把处理结果写入 data/ 目录，并同步到 website/data/。"""
import json
import shutil
from pathlib import Path

from crawler.config import DATA_DIR, DATA_FILES, WEBSITE_DATA_DIR

_FILE_NAMES = ("models.json", "today.json", "history.json", "promotions.json")


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def export_models(models):
    return save_json(DATA_FILES["models"], models)


def export_today(today):
    return save_json(DATA_FILES["today"], today)


def export_history(history):
    return save_json(DATA_FILES["history"], history)


def export_promotions(promotions):
    return save_json(DATA_FILES["promotions"], promotions)


def sync_to_website():
    """把 data/ 最新数据同步到 website/data/，供 Cloudflare Pages 静态发布。"""
    WEBSITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in _FILE_NAMES:
        src = DATA_DIR / name
        if src.exists():
            shutil.copy2(src, WEBSITE_DATA_DIR / name)
            copied.append(name)
    return WEBSITE_DATA_DIR, copied
