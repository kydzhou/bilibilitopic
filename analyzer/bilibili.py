"""Bilibili search client with WBI signature support."""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import reduce
from typing import Any
from urllib.parse import quote

import httpx

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
    "Origin": "https://www.bilibili.com",
}


@dataclass
class VideoItem:
    bvid: str
    title: str
    author: str
    play: int
    danmaku: int
    pubdate: datetime
    description: str
    tag: str
    duration: str
    url: str


@dataclass
class HotKeyword:
    rank: int
    keyword: str
    label: str


def _mixin_key(img_key: str, sub_key: str) -> str:
    raw = img_key + sub_key
    return reduce(lambda acc, index: acc + raw[index], MIXIN_KEY_ENC_TAB, "")[:32]


def _encodeURIComponent(value: str) -> str:
    encoded = quote(str(value), safe="")
    return re.sub(
        r"%([0-9a-fA-F]{2})",
        lambda match: f"%{match.group(1).upper()}",
        encoded,
    )


def _sign_params(params: dict[str, Any], img_key: str, sub_key: str) -> dict[str, Any]:
    signed = dict(params)
    signed["wts"] = int(time.time())
    signed = dict(sorted(signed.items()))
    signed = {
        key: "".join(ch for ch in str(value) if ch not in "!'()*")
        for key, value in signed.items()
    }
    query = "&".join(f"{key}={_encodeURIComponent(value)}" for key, value in signed.items())
    signed["w_rid"] = hashlib.md5((query + _mixin_key(img_key, sub_key)).encode()).hexdigest()
    return signed


class BilibiliClient:
    def __init__(self, timeout: float = 20.0) -> None:
        self._timeout = timeout
        self._img_key: str | None = None
        self._sub_key: str | None = None
        self._keys_fetched_at: float = 0.0
        self._buvid3: str | None = None

    def _client(self) -> httpx.Client:
        headers = dict(DEFAULT_HEADERS)
        cookies: dict[str, str] = {}
        if self._buvid3:
            cookies["buvid3"] = self._buvid3
        return httpx.Client(
            headers=headers,
            cookies=cookies,
            timeout=self._timeout,
            follow_redirects=True,
        )

    def _ensure_buvid3(self, client: httpx.Client) -> None:
        if self._buvid3:
            return
        response = client.get("https://api.bilibili.com/x/frontend/finger/spi")
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") == 0:
            self._buvid3 = payload["data"]["b_3"]
            return
        response = client.get("https://www.bilibili.com/")
        for cookie in response.cookies.jar:
            if cookie.name == "buvid3":
                self._buvid3 = cookie.value
                return
        raise RuntimeError("无法获取 buvid3，B站接口鉴权失败")

    def _ensure_wbi_keys(self, client: httpx.Client) -> None:
        if self._img_key and self._sub_key and time.time() - self._keys_fetched_at < 3600:
            return
        response = client.get("https://api.bilibili.com/x/web-interface/nav")
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or {}
        wbi_img = data.get("wbi_img")
        if not wbi_img:
            raise RuntimeError(f"获取 WBI 密钥失败: {payload.get('message', payload)}")
        self._img_key = wbi_img["img_url"].rsplit("/", 1)[1].split(".")[0]
        self._sub_key = wbi_img["sub_url"].rsplit("/", 1)[1].split(".")[0]
        self._keys_fetched_at = time.time()

    def _signed_get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        with self._client() as client:
            self._ensure_buvid3(client)
            self._ensure_wbi_keys(client)
            signed = _sign_params(params, self._img_key or "", self._sub_key or "")
            if self._buvid3:
                client.cookies.set("buvid3", self._buvid3)
            response = client.get(url, params=signed)
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 0:
                raise RuntimeError(f"B站 API 错误: {payload.get('message', payload)}")
            return payload

    def search_videos(
        self,
        keyword: str,
        *,
        page: int = 1,
        page_size: int = 20,
        order: str = "pubdate",
        days: int | None = None,
    ) -> list[VideoItem]:
        params: dict[str, Any] = {
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "order": order,
        }
        payload = self._signed_get(
            "https://api.bilibili.com/x/web-interface/wbi/search/type",
            params,
        )
        result = payload.get("data", {}).get("result") or []
        cutoff = None
        if days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        videos: list[VideoItem] = []
        for item in result:
            pub_ts = item.get("pubdate")
            if not pub_ts:
                continue
            pubdate = datetime.fromtimestamp(int(pub_ts), tz=timezone.utc)
            if cutoff and pubdate < cutoff:
                continue
            bvid = item.get("bvid") or ""
            videos.append(
                VideoItem(
                    bvid=bvid,
                    title=_strip_markup(item.get("title", "")),
                    author=item.get("author", ""),
                    play=int(item.get("play", 0) or 0),
                    danmaku=int(item.get("danmaku", 0) or 0),
                    pubdate=pubdate,
                    description=_strip_markup(item.get("description", "")),
                    tag=item.get("tag", ""),
                    duration=item.get("duration", ""),
                    url=f"https://www.bilibili.com/video/{bvid}" if bvid else "",
                )
            )
        return videos

    def fetch_recent_videos(
        self,
        keyword: str,
        *,
        limit: int = 30,
        days: int = 30,
        order: str = "pubdate",
    ) -> list[VideoItem]:
        collected: list[VideoItem] = []
        page = 1
        while len(collected) < limit and page <= 5:
            batch = self.search_videos(
                keyword,
                page=page,
                page_size=min(50, limit),
                order=order,
                days=days,
            )
            if not batch:
                break
            for video in batch:
                if video.bvid and all(existing.bvid != video.bvid for existing in collected):
                    collected.append(video)
                    if len(collected) >= limit:
                        break
            page += 1
        return collected[:limit]

    def get_hot_keywords(self, limit: int = 20) -> list[HotKeyword]:
        with self._client() as client:
            response = client.get(
                "https://s.search.bilibili.com/main/hotword",
                params={"limit": limit},
            )
            response.raise_for_status()
            payload = response.json()
        items = payload.get("list") or []
        hot_list: list[HotKeyword] = []
        for item in items[:limit]:
            hot_list.append(
                HotKeyword(
                    rank=int(item.get("pos") or item.get("position") or 0),
                    keyword=item.get("show_name") or item.get("keyword") or "",
                    label=_hot_label(item.get("word_type")),
                )
            )
        return hot_list


def _strip_markup(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _hot_label(word_type: Any) -> str:
    mapping = {
        4: "新",
        5: "热",
        7: "直播",
        9: "梗",
        11: "话题",
        12: "独家",
    }
    return mapping.get(int(word_type or 0), "")


def format_videos_for_llm(videos: list[VideoItem]) -> str:
    if not videos:
        return "（未找到相关视频）"
    lines: list[str] = []
    for index, video in enumerate(videos, start=1):
        pub = video.pubdate.astimezone().strftime("%Y-%m-%d")
        lines.append(
            f"{index}. 《{video.title}》\n"
            f"   UP主: {video.author} | 播放: {video.play:,} | 弹幕: {video.danmaku:,} | 发布: {pub}\n"
            f"   标签: {video.tag or '无'} | 时长: {video.duration or '未知'}\n"
            f"   简介: {video.description[:120] or '无'}\n"
            f"   链接: {video.url}"
        )
    return "\n\n".join(lines)
