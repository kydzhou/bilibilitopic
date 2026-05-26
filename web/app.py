"""FastAPI web application."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from analyzer.bilibili import BilibiliClient
from analyzer.llm import load_llm_config
from analyzer.service import AnalysisRequest, run_analysis, result_to_dict

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

load_dotenv()
load_dotenv(PROJECT_DIR / ".env")

app = FastAPI(title="B站话题分析", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class AnalyzeBody(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    days: int = Field(30, ge=1, le=90)
    limit: int = Field(25, ge=5, le=80)
    order: str = Field("pubdate", pattern="^(pubdate|totalrank|click)$")
    include_hot: bool = True


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health() -> dict:
    status = {"bilibili": "ok", "llm": "ok"}
    try:
        load_llm_config()
    except RuntimeError as exc:
        status["llm"] = str(exc)
    try:
        BilibiliClient().get_hot_keywords(1)
    except Exception as exc:
        status["bilibili"] = str(exc)
    return status


@app.get("/api/trending")
async def trending(limit: int = 20) -> dict:
    limit = max(1, min(limit, 50))
    try:
        items = BilibiliClient().get_hot_keywords(limit)
        return {
            "items": [
                {"rank": item.rank, "keyword": item.keyword, "label": item.label}
                for item in items
            ]
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"B站热搜获取失败: {exc}") from exc


@app.post("/api/analyze")
async def analyze(body: AnalyzeBody) -> dict:
    try:
        result = run_analysis(
            AnalysisRequest(
                keyword=body.keyword,
                days=body.days,
                limit=body.limit,
                order=body.order,
                include_hot=body.include_hot,
            )
        )
        return result_to_dict(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"分析失败: {exc}") from exc


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("web.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
