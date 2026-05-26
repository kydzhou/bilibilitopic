"""FastAPI web application."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from analyzer.bilibili import BilibiliClient
from analyzer.llm import make_llm_config
from analyzer.service import AnalysisRequest, run_analysis, result_to_dict

BASE_DIR = Path(__file__).resolve().parent


def normalize_base_path(raw: str) -> str:
    value = raw.strip()
    if not value or value == "/":
        return ""
    if not value.startswith("/"):
        value = f"/{value}"
    return value.rstrip("/")


BASE_PATH = normalize_base_path(os.getenv("BASE_PATH", ""))


class LLMBody(BaseModel):
    api_key: str = Field(..., min_length=1, max_length=500)
    base_url: str = Field("https://api.openai.com/v1", max_length=500)
    model: str = Field("gpt-4o-mini", max_length=100)


class AnalyzeBody(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    days: int = Field(30, ge=1, le=90)
    limit: int = Field(25, ge=5, le=80)
    order: str = Field("pubdate", pattern="^(pubdate|totalrank|click)$")
    include_hot: bool = True
    llm: LLMBody


def create_app(base_path: str = "") -> FastAPI:
    app = FastAPI(title="B站话题分析", version="1.0.0")
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=BASE_DIR / "templates")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "base_path": base_path,
                "base_path_json": json.dumps(base_path),
            },
        )

    @app.get("/api/health")
    async def health() -> dict:
        status = {"bilibili": "ok", "llm": "由浏览器填写", "base_path": base_path or "/"}
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
            llm_config = make_llm_config(
                body.llm.api_key,
                base_url=body.llm.base_url,
                model=body.llm.model,
            )
            result = run_analysis(
                AnalysisRequest(
                    keyword=body.keyword,
                    days=body.days,
                    limit=body.limit,
                    order=body.order,
                    include_hot=body.include_hot,
                    llm_config=llm_config,
                )
            )
            return result_to_dict(result)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"分析失败: {exc}") from exc

    return app


inner_app = create_app(BASE_PATH)

if BASE_PATH:
    application = FastAPI()

    @application.get(BASE_PATH, include_in_schema=False)
    async def redirect_to_slash() -> RedirectResponse:
        return RedirectResponse(url=f"{BASE_PATH}/", status_code=301)

    application.mount(BASE_PATH, inner_app)
else:
    application = inner_app


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("web.app:application", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
