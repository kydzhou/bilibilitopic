"""Command-line interface."""

from __future__ import annotations

from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from analyzer.bilibili import BilibiliClient
from analyzer.llm import load_llm_config
from analyzer.service import AnalysisRequest, run_analysis

app = typer.Typer(
    add_completion=False,
    help="通过关键词抓取 B 站近期视频，并用 LLM 分析话题趋势。",
)
console = Console()


def _load_env() -> None:
    load_dotenv()
    project_env = Path(__file__).resolve().parent.parent / ".env"
    if project_env.exists():
        load_dotenv(project_env)


@app.command("analyze")
def analyze_command(
    keyword: str = typer.Argument(..., help="要分析的关键词"),
    days: int = typer.Option(30, "--days", "-d", min=1, max=90, help="回溯天数"),
    limit: int = typer.Option(25, "--limit", "-l", min=5, max=80, help="抓取视频数量"),
    order: str = typer.Option(
        "totalrank",
        "--order",
        "-o",
        help="排序：totalrank(综合) / pubdate(最新) / click(时间范围内播放量)",
    ),
    save: Path | None = typer.Option(None, "--save", "-s", help="将报告保存为 Markdown 文件"),
) -> None:
    """抓取近期视频并生成 LLM 话题分析报告。"""
    _load_env()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(description=f"正在分析「{keyword}」...", total=None)
        result = run_analysis(
            AnalysisRequest(
                keyword=keyword,
                days=days,
                limit=limit,
                order=order,
            )
        )

    console.print()
    console.print(
        Panel(
            f"关键词: [bold cyan]{result.keyword}[/] | 样本: {result.video_count} 条 | 近 {result.days} 天 | 排序: {result.order}",
            title="B站话题分析",
            border_style="cyan",
        )
    )
    console.print()
    console.print(Markdown(result.report))

    if save:
        save.parent.mkdir(parents=True, exist_ok=True)
        header = (
            f"# B站话题分析：{result.keyword}\n\n"
            f"- 生成时间: {result.generated_at}\n"
            f"- 样本数量: {result.video_count}\n"
            f"- 时间范围: 近 {result.days} 天\n\n"
        )
        save.write_text(header + result.report, encoding="utf-8")
        console.print(f"\n[green]报告已保存:[/] {save}")


@app.command("search")
def search_command(
    keyword: str = typer.Argument(..., help="搜索关键词"),
    days: int = typer.Option(30, "--days", "-d", min=1, max=90),
    limit: int = typer.Option(10, "--limit", "-l", min=1, max=50),
    order: str = typer.Option("pubdate", "--order", "-o"),
) -> None:
    """仅搜索视频，不调用 LLM（用于调试数据）。"""
    client = BilibiliClient()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(description="搜索中...", total=None)
        videos = client.fetch_recent_videos(keyword, limit=limit, days=days, order=order)

    table = Table(title=f"「{keyword}」近期视频")
    table.add_column("#", style="dim")
    table.add_column("标题")
    table.add_column("UP主")
    table.add_column("播放", justify="right")
    table.add_column("发布")

    for index, video in enumerate(videos, start=1):
        table.add_row(
            str(index),
            video.title[:40],
            video.author[:12],
            f"{video.play:,}",
            video.pubdate.astimezone().strftime("%m-%d"),
        )

    console.print(table)


@app.command("trending")
def trending_command(
    limit: int = typer.Option(20, "--limit", "-l", min=1, max=50),
) -> None:
    """查看 B 站当前热搜词。"""
    client = BilibiliClient()
    items = client.get_hot_keywords(limit)

    table = Table(title="B站热搜")
    table.add_column("排名", justify="right")
    table.add_column("关键词")
    table.add_column("标签")

    for item in items:
        table.add_row(str(item.rank), item.keyword, item.label or "-")

    console.print(table)


@app.command("check")
def check_command() -> None:
    """检查 API Key 与 B 站接口连通性。"""
    _load_env()
    console.print("[bold]检查配置...[/]")

    try:
        cfg = load_llm_config()
        console.print(f"  LLM: [green]OK[/] ({cfg.model} @ {cfg.base_url})")
    except RuntimeError as exc:
        console.print(f"  LLM: [red]FAIL[/] {exc}")

    try:
        client = BilibiliClient()
        hot = client.get_hot_keywords(3)
        console.print(f"  B站热搜: [green]OK[/] ({len(hot)} 条)")
        videos = client.fetch_recent_videos("科技", limit=3, days=30)
        console.print(f"  B站搜索: [green]OK[/] (示例 {len(videos)} 条视频)")
    except Exception as exc:
        console.print(f"  B站接口: [red]FAIL[/] {exc}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
