"""OpenAI-compatible LLM analysis."""

from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str


def make_llm_config(
    api_key: str,
    *,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
) -> LLMConfig:
    key = api_key.strip()
    if not key:
        raise RuntimeError("请填写 API Key")
    url = base_url.strip() or "https://api.openai.com/v1"
    name = model.strip() or "gpt-4o-mini"
    return LLMConfig(api_key=key, base_url=url, model=name)


def load_llm_config() -> LLMConfig:
    """Load LLM config from environment (CLI only)."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("未设置 OPENAI_API_KEY，CLI 模式请在环境变量中配置")
    return make_llm_config(
        api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )


ANALYSIS_SYSTEM_PROMPT = """你是一位熟悉 B 站生态的中文内容分析师。
用户会提供一个「搜索关键词」，以及按该关键词在 B 站搜索得到的近期视频样本。
你的任务是分析该搜索关键词相关的话题趋势。

要求：
- 使用中文
- 分析对象必须是用户提供的搜索关键词及其视频样本
- 基于样本推断，不要编造不存在的具体事件或 UP 主
- 若样本不足，明确说明局限性
- 分析要有洞察，避免空泛套话
"""


def build_analysis_prompt(
    keyword: str,
    videos_text: str,
    *,
    days: int,
) -> str:
    return f"""请分析 B 站近期与搜索关键词「{keyword}」相关的话题趋势。

【重要】本次分析主题 = 搜索关键词「{keyword}」。
视频样本均来自 B 站搜索框搜索「{keyword}」的结果。

数据范围：近 {days} 天内抓取的视频样本（按用户选择的排序方式）。

视频样本（搜索「{keyword}」得到）：
{videos_text}

请按以下结构输出 Markdown 报告（围绕搜索关键词「{keyword}」展开）：

## 话题概览
（1-2 段，总结该关键词在 B 站近期的整体热度与走向）

## 热门子话题
（列出 3-6 个细分方向，每个用 1-2 句话说明）

## 内容特征
（标题/封面/叙事/玩梗/情绪等共性，结合样本举例）

## 受众与传播
（谁在看、为什么传播、互动信号如播放/弹幕反映什么）

## 创作机会
（若 UP 主或品牌要跟进，可切入的 2-4 个角度）

## 风险与注意
（敏感点、同质化、时效性等）

## 样本局限
（样本量、时间窗口、搜索偏差等）
"""


def analyze_topic(
    keyword: str,
    videos_text: str,
    *,
    days: int,
    config: LLMConfig | None = None,
) -> str:
    cfg = config or load_llm_config()
    client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
    response = client.chat.completions.create(
        model=cfg.model,
        messages=[
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_analysis_prompt(
                    keyword,
                    videos_text,
                    days=days,
                ),
            },
        ],
        temperature=0.6,
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("LLM 返回空内容")
    return content.strip()
