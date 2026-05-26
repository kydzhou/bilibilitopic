"""Shared analysis service for CLI and Web."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from analyzer.bilibili import MIN_PLAY_COUNT, BilibiliClient, VideoItem, format_videos_for_llm
from analyzer.llm import LLMConfig, analyze_topic


@dataclass
class AnalysisRequest:
    keyword: str
    days: int = 30
    limit: int = 25
    llm_config: LLMConfig | None = None


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
    min_play: int
    video_count: int
    videos: list[VideoSummary]
    report: str
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
        raise ValueError("搜索关键词不能为空")

    client = BilibiliClient()
    videos = client.fetch_recent_videos(
        keyword,
        limit=request.limit,
        days=request.days,
        min_play=MIN_PLAY_COUNT,
    )
    if not videos:
        raise ValueError(
            f"近 {request.days} 天内未找到播放 ≥ {MIN_PLAY_COUNT:,} 的相关视频，"
            "请换关键词、扩大回溯天数或减少样本数量"
        )

    videos_text = format_videos_for_llm(videos)
    report = analyze_topic(
        keyword,
        videos_text,
        days=request.days,
        min_play=MIN_PLAY_COUNT,
        config=request.llm_config,
    )

    return AnalysisResult(
        keyword=keyword,
        days=request.days,
        limit=request.limit,
        min_play=MIN_PLAY_COUNT,
        video_count=len(videos),
        videos=[_to_summary(video) for video in videos],
        report=report,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def result_to_dict(result: AnalysisResult) -> dict:
    return asdict(result)
