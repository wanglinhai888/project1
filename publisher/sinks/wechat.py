"""微信公众号推送 sink：把 AI 润色文章自动发布到公众号。

支持多公众号：凭据以 JSON 数组放在环境变量 WX_ACCOUNTS 中，例如：
[
  {"appid":"wx...","appsecret":"...","author":"CODENAV","cover":"https://.../cover.png"},
  {"appid":"wx...","appsecret":"...","cover":"https://.../cover2.png"}
]
也支持单号简配：WX_APPID / WX_SECRET / WX_AUTHOR / WX_COVER。

发布流程（均已封装失败降级）：
  get_access_token → upload_thumb(封面) → draft/add(建草稿) → freepublish/submit(发布)
说明：
- 用"发布"接口(freepublish)，订阅号即可用，文章上线到公众号（号主页/历史/可搜索）。
  若要"群发推送给粉丝"，需微信认证的服务号，并把 publish() 换成 message/mass/sendall。
- 封面 thumb_media_id 必填：每个账号在配置里给一个 cover（图片 URL 或本地路径）。
依赖：requests（已在 crawler/requirements.txt）。纯标准库做 Markdown→HTML 转换。
"""
import argparse
import datetime
import html
import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawler.config import DATA_DIR

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


class WeChatError(Exception):
    pass


# ---------- Markdown -> HTML（精简实现，覆盖标题/加粗/链接/列表/段落）----------
def _inline(text):
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    return text


def md_to_html(md):
    if not md:
        return ""
    html_parts = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html_parts.append("</ul>")
            in_list = False

    for line in md.split("\n"):
        s = line.strip()
        if not s:
            close_list()
            continue
        if s.startswith("### "):
            close_list()
            html_parts.append(f"<h3>{_inline(s[4:])}</h3>")
        elif s.startswith("## "):
            close_list()
            html_parts.append(f"<h2>{_inline(s[3:])}</h2>")
        elif s.startswith("# "):
            close_list()
            html_parts.append(f"<h1>{_inline(s[2:])}</h1>")
        elif s.startswith("- "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{_inline(s[2:])}</li>")
        else:
            close_list()
            html_parts.append(f"<p>{_inline(s)}</p>")
    close_list()
    return "\n".join(html_parts)


# ---------- 微信 API ----------
def get_access_token(appid, secret, timeout=30):
    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {"grant_type": "client_credential", "appid": appid, "secret": secret}
    resp = requests.get(url, params=params, timeout=timeout)
    data = resp.json()
    if "access_token" not in data:
        raise WeChatError(data)
    return data["access_token"]


def upload_thumb(token, source, timeout=60):
    """上传封面图，返回 media_id。source 可为 http(s) URL 或本地路径。"""
    if source.startswith("http://") or source.startswith("https://"):
        r = requests.get(source, timeout=timeout)
        r.raise_for_status()
        blob = r.content
        fname = "cover.png"
    else:
        with open(source, "rb") as f:
            blob = f.read()
        fname = os.path.basename(source) or "cover.png"
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
    resp = requests.post(url, files={"media": (fname, blob)}, timeout=timeout)
    data = resp.json()
    if data.get("media_id") is None:
        raise WeChatError(data)
    return data["media_id"]


def create_draft(token, article, thumb_media_id, author="", timeout=60):
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
    content = md_to_html(article.get("article", ""))
    faqs = article.get("faq") or []
    if faqs:
        content += "<h2>常见问题（FAQ）</h2><ul>"
        for f in faqs:
            content += (
                f"<li><strong>{html.escape(f.get('q', ''))}</strong><br>"
                f"{html.escape(f.get('a', ''))}</li>"
            )
        content += "</ul>"
    body = {
        "articles": [
            {
                "title": article.get("title", ""),
                "author": author,
                "digest": (article.get("meta_description") or "")[:120],
                "content": content,
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }
        ]
    }
    resp = requests.post(url, json=body, timeout=timeout)
    data = resp.json()
    if data.get("media_id") is None:
        raise WeChatError(data)
    return data["media_id"]


def publish(token, media_id, timeout=60):
    """发布（freepublish）。返回含 publish_id 的响应；发布为异步，可用 freepublish/get 查询。"""
    url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={token}"
    resp = requests.post(url, json={"media_id": media_id}, timeout=timeout)
    return resp.json()


def publish_account(account, article):
    appid = account.get("appid")
    secret = account.get("appsecret")
    if not appid or not secret:
        return {"appid": appid, "ok": False, "error": "missing appid/appsecret"}
    token = get_access_token(appid, secret)
    cover = account.get("cover") or os.environ.get("WX_DEFAULT_COVER")
    if not cover:
        return {"appid": appid, "ok": False, "error": "no cover image configured"}
    thumb = upload_thumb(token, cover)
    media_id = create_draft(token, article, thumb, account.get("author", ""))
    resp = publish(token, media_id)
    return {"appid": appid, "ok": True, "publish_id": resp.get("publish_id"), "resp": resp}


def load_accounts():
    raw = os.environ.get("WX_ACCOUNTS")
    if raw:
        try:
            accs = json.loads(raw)
            if isinstance(accs, list):
                return accs
        except Exception:
            pass
    appid = os.environ.get("WX_APPID")
    secret = os.environ.get("WX_SECRET")
    if appid and secret:
        return [
            {
                "appid": appid,
                "appsecret": secret,
                "author": os.environ.get("WX_AUTHOR", ""),
                "cover": os.environ.get("WX_COVER", ""),
            }
        ]
    return []


def _find_article_json(explicit=None):
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p
    candidates = sorted(DATA_DIR.glob("article_*.json"))
    if candidates:
        return candidates[-1]
    return None


def main():
    ap = argparse.ArgumentParser(description="微信公众号自动发布（无凭据自动跳过）")
    ap.add_argument("--article", default=None, help="article_*.json 路径，默认取最新")
    args = ap.parse_args()

    if requests is None:
        print("[wechat] 缺少 requests 依赖，跳过公众号推送。")
        return

    accounts = load_accounts()
    if not accounts:
        print("[wechat] 未配置 WX_ACCOUNTS / WX_APPID，跳过公众号推送（不阻断流程）。")
        return

    path = _find_article_json(args.article)
    if not path:
        print("[wechat] 未找到 article_*.json，跳过公众号推送。")
        return

    article = json.loads(Path(path).read_text(encoding="utf-8"))
    print(f"[wechat] 使用文章：{path.name}（{article.get('title','')}）")

    for acc in accounts:
        try:
            res = publish_account(acc, article)
            print("[wechat] 推送结果: " + json.dumps(res, ensure_ascii=False))
        except Exception as exc:  # 单账号失败不影响其他账号
            print(f"[wechat] 账号 {acc.get('appid')} 推送失败，跳过: {exc}")


if __name__ == "__main__":
    main()
