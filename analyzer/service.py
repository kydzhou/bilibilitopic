"""Shared analysis service for CLI and Web."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from analyzer.bilibili import BilibiliClient, VideoItem, format_videos_for_llm
from analyzer.llm import analyze_topic


@dataclass
class AnalysisRequest:
    keyword: str
    days: int = 30
    limit: int = 25
    order: str = "pubdate"
    include_hot: bool = True


@dataclass
class VideoSummary:
    bvid: str
    title: str
    author: str
    play: int
    danmaku: int
    pubdate: str
    tag: str
    duration: str
    url: str


@dataclass
class AnalysisResult:
    keyword: str
    days: int
    limit: int
    order: str
    video_count: int
    videos: list[VideoSummary]
    report: str
    hot_keywords: list[str]
    generated_at: str


def _to_summary(video: VideoItem) -> VideoSummary:
    return VideoSummary(
        bvid=video.bvid,
        title=video.title,
        author=video.author,
        play=video.play,
        danmaku=video.danmaku,
        pubdate=video.pubdate.astimezone().strftime("%Y-%m-%d"),
        tag=video.tag,
        duration=video.duration,
        url=video.url,
    )


def run_analysis(request: AnalysisRequest) -> AnalysisResult:
    keyword = request.keyword.strip()
    if not keyword:
        raise ValueError("关键词不能为空")

    client = BilibiliClient()
    hot_keywords: list[str] = []

    videos = client.fetch_recent_videos(
        keyword,
        limit=request.limit,
        days=request.days,
        order=request.order,
    )

    if request.include_hot:
        try:
            hot_keywords = [item.keyword for item in client.get_hot_keywords(15)]
        except Exception:
            hot_keywords = []

    videos_text = format_videos_for_llm(videos)
    report = analyze_topic(
        keyword,
        videos_text,
        days=request.days,
        hot_keywords=hot_keywords if request.include_hot else None,
    )

    return AnalysisResult(
        keyword=keyword,
        days=request.days,
        limit=request.limit,
        order=request.order,
        video_count=len(videos),
        videos=[_to_summary(video) for video in videos],
        report=report,
        hot_keywords=hot_keywords,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def result_to_dict(result: AnalysisResult) -> dict:
    return asdict(result)
